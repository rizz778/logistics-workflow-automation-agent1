from config.settings import settings
import os
import google.generativeai as genai
import json

def get_gemini_client():
    """Initializes and returns the configured genai client module."""
    api_key = settings.gemini_api_key or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set in your .env or system environment.")
    genai.configure(api_key=api_key)
    return genai

def load_rules() -> dict:
    """Loads rules from config or falls back to defaults."""
    if os.path.exists(settings.rules_path):
        try:
            with open(settings.rules_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("rules", {})
        except Exception as e:
            print(f"Error loading rules.json: {e}")
            
    # Default fallback rules
    return {
        "consignee_name": {"type": "exact_match", "expected": "Nova Logistics Ltd"},
        "hs_code": {"type": "prefix_match", "expected_prefixes": ["8708"]},
        "incoterms": {"type": "allow_list", "expected": ["FOB", "CIF"]}
    }
