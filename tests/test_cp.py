import asyncio
from config.settings import settings
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

async def main():
    print(f"Testing AsyncPostgresSaver with URL:")
    # mask password
    parts = settings.database_url.split("@")
    print(f"Target: ...@{parts[-1]}")
    try:
        saver = AsyncPostgresSaver.from_conn_string(settings.database_url)
        await saver.__aenter__()
        print("Connected! Running saver.setup()...")
        await saver.setup()
        print(">>> SUCCESS: LangGraph AsyncPostgresSaver connected and setup completed! <<<")
        await saver.__aexit__(None, None, None)
    except Exception as e:
        print(f"\n>>> FAILED: {type(e).__name__}: {e}\n")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
