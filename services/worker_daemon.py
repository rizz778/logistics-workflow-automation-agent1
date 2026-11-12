import asyncio
import json
import logging
import signal
from typing import Dict, Any, Optional

import redis.asyncio as aioredis
from langgraph.types import Command
from langgraph.errors import GraphInterrupt

from config.settings import settings
from db.checkpointer import checkpointer_manager
from graph.graph import create_pipeline
from services.s3_service import s3_service
from services.db_service import db_service

logger = logging.getLogger("agent_worker.daemon")

class TradeDocWorkerDaemon:
    """Asynchronous worker consuming shipment validation tasks from Redis Streams.
    - Manages LangGraph execution with durable PostgreSQL/Memory checkpoints.
    - Resumes interrupted workflows (HitL human correction and approval).
    - Enforces 3-retry backoff policy and Dead Letter Queue (DLQ) routing.
    """

    def __init__(self):
        self.redis_url = settings.redis_url
        self.stream_name = settings.redis_queue_name
        self.group_name = settings.redis_consumer_group
        self.consumer_name = settings.redis_consumer_name
        self.dlq_stream_name = f"{self.stream_name}_dlq"
        self._running = False
        self._redis: Optional[aioredis.Redis] = None

    async def _init_consumer_group(self, redis: aioredis.Redis) -> None:
        """Initializes the Redis Streams consumer group if it does not already exist."""
        try:
            await redis.xgroup_create(
                name=self.stream_name,
                groupname=self.group_name,
                id="0",
                mkstream=True
            )
            logger.info("Created consumer group '%s' on stream '%s'.", self.group_name, self.stream_name)
        except Exception as e:
            if "BUSYGROUP" in str(e):
                logger.debug("Consumer group '%s' already exists.", self.group_name)
            else:
                logger.warning("Could not create consumer group (%s). Will attempt to read stream directly.", e)

    async def start(self) -> None:
        """Starts the worker daemon event loop."""
        self._running = True
        logger.info(
            "Starting Trade Document Agent Worker [Queue: %s | Group: %s | Consumer: %s]...",
            self.stream_name, self.group_name, self.consumer_name
        )

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, self.stop)
            except NotImplementedError:
                pass

        try:
            self._redis = aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=3.0
            )
            await self._init_consumer_group(self._redis)
        except Exception as e:
            logger.error("Failed to connect to Redis at %s: %s", self.redis_url, e)
            logger.info("Worker daemon will idle in polling mode until Redis is online.")

        while self._running:
            try:
                if self._redis is None:
                    await asyncio.sleep(2.0)
                    try:
                        self._redis = aioredis.from_url(
                            self.redis_url,
                            encoding="utf-8",
                            decode_responses=True,
                            socket_connect_timeout=3.0
                        )
                        await self._init_consumer_group(self._redis)
                    except Exception:
                        continue

                entries = await self._redis.xreadgroup(
                    groupname=self.group_name,
                    consumername=self.consumer_name,
                    streams={self.stream_name: ">"},
                    count=1,
                    block=2000
                )

                if not entries:
                    await asyncio.sleep(0.1)
                    continue

                for stream_key, messages in entries:
                    for message_id, raw_data in messages:
                        await self._handle_message(message_id, raw_data)

            except asyncio.CancelledError:
                logger.info("Worker event loop cancelled.")
                break
            except Exception as e:
                logger.error("Unexpected error in worker consumer loop: %s", e)
                await asyncio.sleep(1.0)

        logger.info("Worker daemon stopped gracefully.")

    def stop(self) -> None:
        """Signals worker daemon to stop consuming."""
        logger.info("Shutdown signal received. Stopping worker daemon...")
        self._running = False

    async def _handle_message(self, message_id: str, raw_data: Dict[str, Any]) -> None:
        """Parses and executes a single task event."""
        logger.info("Received queue event [ID: %s]", message_id)

        try:
            payload_str = raw_data.get("payload") or raw_data.get("data")
            if payload_str:
                event = json.loads(payload_str)
            else:
                event = raw_data

            shipment_id = event.get("shipment_id")
            event_type = event.get("event_type", "INITIAL_PROCESS")
            retry_count = int(event.get("retry_count", 0))

            logger.info("Processing shipment '%s' (Event: %s, Retry: %d)", shipment_id, event_type, retry_count)
            await self._execute_pipeline(message_id, event)

        except Exception as e:
            logger.exception("Error processing message %s: %s", message_id, e)
            await self._handle_failure(message_id, raw_data, e)

    async def _execute_pipeline(self, message_id: str, event: Dict[str, Any]) -> None:
        """Executes or resumes the LangGraph compliance workflow."""
        shipment_id = event.get("shipment_id")
        run_id = event.get("run_id")
        event_type = event.get("event_type", "INITIAL_PROCESS")
        files = event.get("files", [])

        config = {"configurable": {"thread_id": shipment_id}}

        async with checkpointer_manager.get_checkpointer() as checkpointer:
            graph = create_pipeline(checkpointer=checkpointer)

            # Case A: Initial Document Ingestion & Compliance Run
            if event_type in ("INITIAL_PROCESS", "RETRY"):
                logger.info("Streaming document files from S3 for shipment '%s'...", shipment_id)
                file_bytes_map = s3_service.download_shipment_files(files)

                await db_service.update_run_status(shipment_id, "processing")

                initial_state = {
                    "shipment_id": shipment_id,
                    "run_id": run_id,
                    "filenames": [f.get("filename") for f in files if f.get("filename")],
                    "files": files,
                    "file_bytes_map": file_bytes_map,
                    "status": "extracting",
                    "extraction_retry_count": 0,
                    "source": event.get("source", "manual_upload"),
                    "email_sender": event.get("email_sender"),
                    "email_metadata": event.get("email_metadata"),
                    "logs": [f"Worker: Task {shipment_id} started on {self.consumer_name}"]
                }

                try:
                    final_state = await graph.ainvoke(initial_state, config=config)

                    logger.info("Pipeline completed successfully for shipment '%s'. Decision: '%s'",
                                shipment_id, final_state.get("decision"))

                    await db_service.update_run_outcomes(
                        shipment_id=shipment_id,
                        extracted_data=final_state.get("extracted_data", {}),
                        validation_results=final_state.get("validation_results", {}),
                        decision=final_state.get("decision", "auto_approve"),
                        decision_reason=final_state.get("decision_reason", ""),
                        amendment_draft=final_state.get("amendment_draft"),
                        status=final_state.get("status", "approved"),
                        cross_doc_results=final_state.get("cross_doc_results")
                    )

                except GraphInterrupt as gi:
                    logger.info("Pipeline interrupted for HitL intervention on shipment '%s'. Details: %s",
                                shipment_id, gi.args[0] if gi.args else "")

                    state_snapshot = await graph.aget_state(config)
                    next_nodes = state_snapshot.next if state_snapshot else ()

                    if "human_correction" in next_nodes:
                        await db_service.update_run_status(shipment_id, "pending_correction")
                    else:
                        await db_service.update_run_status(shipment_id, "pending_review")

            # Case B: Human Operator Resumes from Checkpoint
            elif event_type == "HUMAN_EDIT_REPROCESS":
                logger.info("Resuming shipment '%s' from checkpoint with human edits...", shipment_id)

                run_record = await db_service.get_run(shipment_id)
                human_edits = (run_record.get("edited_data") if run_record else None) or event.get("edited_data") or {}

                try:
                    final_state = await graph.ainvoke(Command(resume=human_edits), config=config)

                    logger.info("Resumed workflow completed for shipment '%s'. New decision: '%s'",
                                shipment_id, final_state.get("decision"))

                    await db_service.update_run_outcomes(
                        shipment_id=shipment_id,
                        extracted_data=final_state.get("extracted_data", {}),
                        validation_results=final_state.get("validation_results", {}),
                        decision=final_state.get("decision", "auto_approve"),
                        decision_reason=final_state.get("decision_reason", ""),
                        amendment_draft=final_state.get("amendment_draft"),
                        status=final_state.get("status", "approved"),
                        cross_doc_results=final_state.get("cross_doc_results")
                    )

                except GraphInterrupt as gi:
                    logger.info("Resumed workflow paused again on HitL node for '%s': %s",
                                shipment_id, gi.args[0] if gi.args else "")
                    await db_service.update_run_status(shipment_id, "pending_review")

        if self._redis:
            await self._redis.xack(self.stream_name, self.group_name, message_id)
            logger.info("Message %s acknowledged in Redis queue.", message_id)

    async def _handle_failure(self, message_id: str, raw_data: Dict[str, Any], error: Exception) -> None:
        """Handles task failure: retries up to 3 times before pushing to Dead Letter Queue (DLQ)."""
        if not self._redis:
            return

        try:
            payload_str = raw_data.get("payload") or raw_data.get("data")
            event = json.loads(payload_str) if payload_str else dict(raw_data)
        except Exception:
            event = dict(raw_data)

        shipment_id = event.get("shipment_id", "unknown")
        retry_count = int(event.get("retry_count", 0)) + 1
        max_retries = int(event.get("max_retries", 3))

        if retry_count <= max_retries:
            backoff_delay = 2 ** retry_count
            logger.warning(
                "Task '%s' failed (Attempt %d/%d). Retrying in %ds... Error: %s",
                shipment_id, retry_count, max_retries, backoff_delay, error
            )

            event["retry_count"] = retry_count
            event["event_type"] = "RETRY"
            event["last_error"] = str(error)

            await asyncio.sleep(backoff_delay)
            await self._redis.xadd(self.stream_name, {"payload": json.dumps(event)})
            await self._redis.xack(self.stream_name, self.group_name, message_id)

        else:
            logger.error(
                "🚨 Task '%s' failed %d retries. Pushing to Dead Letter Queue '%s'...",
                shipment_id, max_retries, self.dlq_stream_name
            )

            event["final_error"] = str(error)
            event["status"] = "dlq_exhausted"

            await self._redis.xadd(self.dlq_stream_name, {"payload": json.dumps(event)})
            await db_service.update_run_status(shipment_id, "failed")
            await self._redis.xack(self.stream_name, self.group_name, message_id)

