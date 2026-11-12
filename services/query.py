import sqlite3
import json
from config.llm import get_llm
from services.storage import get_db_connection
from prompts.npl_query import DB_SCHEMA_PROMPT

def execute_nl_query(user_query: str) -> dict:
    llm = get_llm()
    
    # 1. Ask LLM to generate the SQL query
    try:
        sql_generation_prompt = [
            {"role": "system", "content": DB_SCHEMA_PROMPT},
            {"role": "user", "content": f"Generate the SQL query for: {user_query}"}
        ]
        response = llm.invoke(sql_generation_prompt)
        sql_query = response.content.strip()
        
        # Clean potential markdown wrapping if LLM ignored instructions
        if sql_query.startswith("```"):
            lines = sql_query.splitlines()
            if lines[0].startswith("```sql") or lines[0].startswith("```"):
                sql_query = "\n".join(lines[1:-1]).strip()
                
        # Validate that it is a SELECT query
        if not sql_query.lower().startswith("select"):
            raise ValueError(f"Generated query is not a SELECT statement: {sql_query}")
            
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to generate SQL: {str(e)}",
            "sql": None,
            "answer": "Sorry, I couldn't translate your question to database instructions."
        }
        
    # 2. Execute SQL query on SQLite
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql_query)
            rows = cursor.fetchall()
            results = [dict(r) for r in rows]
    except Exception as e:
        return {
            "success": False,
            "error": f"SQL Execution Error: {str(e)}",
            "sql": sql_query,
            "answer": f"I generated the SQL query `{sql_query}`, but executing it failed: {str(e)}"
        }
        
    # 3. Ask LLM to synthesize the results into a friendly markdown response
    try:
        synthesize_prompt = [
            {"role": "system", "content": "You are a helpful logistics assistant. Analyze the SQLite database query results and provide a friendly, grounded, and concise answer to the user's question."},
            {"role": "user", "content": f"User question: {user_query}\nExecuted SQL: {sql_query}\nQuery Results: {json.dumps(results)}\n\nPlease synthesize a final user-facing answer."}
        ]
        s_response = llm.invoke(synthesize_prompt)
        answer = s_response.content.strip()
    except Exception as e:
        answer = f"Found {len(results)} matching records: {json.dumps(results)}"
        
    return {
        "success": True,
        "sql": sql_query,
        "results": results,
        "answer": answer
    }
