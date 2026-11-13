import io
import logging
import socket
from urllib.parse import urlparse
from typing import Dict, List, Optional
import boto3
from botocore.config import Config
from config.settings import settings

logger = logging.getLogger("agent_worker.s3_service")

def is_socket_reachable(host: str, port: int, timeout: float = 2.5) -> bool:
    """Fast non-blocking probe to avoid connection hangs if S3/MinIO is offline."""
    target_host = "127.0.0.1" if host in ("localhost", "127.0.0.1") else host
    try:
        with socket.create_connection((target_host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False

class S3ReaderService:
    """Streams document bytes directly from S3/MinIO in-memory without buffering on local disk."""

    def __init__(self):
        self.bucket_name = settings.s3_bucket_name
        self.endpoint_url = settings.s3_endpoint_url
        self.access_key = settings.s3_access_key_id
        self.secret_key = settings.s3_secret_access_key
        self.region = settings.s3_region

        parsed = urlparse(self.endpoint_url) if self.endpoint_url else None
        self.host = parsed.hostname or "127.0.0.1" if parsed else "127.0.0.1"
        self.port = parsed.port or (443 if parsed and parsed.scheme == "https" else 9000) if parsed else 9000

        self._client = None

    def _get_client(self):
        if self._client is None:
            self._client = boto3.client(
                "s3",
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region,
                config=Config(signature_version="s3v4", s3={"addressing_style": "path"})
            )
        return self._client

    def download_file_bytes(self, s3_key: str) -> Optional[bytes]:
        """Fetches object bytes directly from S3 bucket into memory."""
        client = self._get_client()
        if not client:
            logger.warning("S3 storage unreachable at %s:%s. Cannot fetch %s", self.host, self.port, s3_key)
            return None

        try:
            response = client.get_object(Bucket=self.bucket_name, Key=s3_key)
            return response["Body"].read()
        except Exception as e:
            logger.error("Failed to read %s from S3 bucket %s: %s", s3_key, self.bucket_name, e)
            return None

    def download_shipment_files(self, files: List[Dict[str, str]]) -> Dict[str, bytes]:
        """Downloads all document files for a shipment into an in-memory dictionary keyed by filename."""
        result: Dict[str, bytes] = {}
        for file_item in files:
            filename = file_item.get("filename")
            s3_key = file_item.get("s3_key")
            if not filename or not s3_key:
                continue

            data = self.download_file_bytes(s3_key)
            if data is not None:
                result[filename] = data
                logger.info("Successfully streamed %s (%d bytes) from S3.", filename, len(data))
            else:
                logger.warning("Could not download %s from S3 key %s.", filename, s3_key)
        return result

s3_service = S3ReaderService()

