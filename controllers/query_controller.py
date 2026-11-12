from fastapi import HTTPException
from services.query import execute_nl_query

async def handle_database_query(payload: dict) -> dict:
    query = payload.get("query")
    if not query:
        raise HTTPException(status_code=400, detail="Missing required 'query' field.")
    try:
        return execute_nl_query(query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to run database query: {str(e)}")
