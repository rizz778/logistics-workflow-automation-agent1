import os
import json
from fastapi import HTTPException
from config.settings import settings

def get_absolute_path(path: str) -> str:
    if os.path.isabs(path):
        return path
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.abspath(os.path.join(backend_dir, path))

async def get_rules() -> dict:
    rules_path = get_absolute_path(settings.rules_path)
    try:
        with open(rules_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read rules configuration: {str(e)}")
