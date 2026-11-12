import re



def clean_weight(weight_str: str | None) -> float | None:
    """Parses a float weight from a string like '1,250.50 kg' or '450 KG'."""
    if not weight_str:
        return None
    try:
        # Strip commas, units, whitespace, and keep decimals
        cleaned = re.sub(r"[^\d.]", "", weight_str)
        return float(cleaned)
    except Exception:
        return None


def validate_field(field_name: str, rule: dict, extracted_value: str | None) -> tuple[str, str | None, str | None, str]:
    """Deterministically checks a field's value against its rule definition."""
    if not rule:
        return "match", None, extracted_value, "No rule defined. Defaults to match."
        
    rule_type = rule.get("type")
    
    # Check if value was extracted at all
    if extracted_value is None or str(extracted_value).strip() == "" or str(extracted_value).lower() == "null":
        return "skipped", None, "null", f"Field '{field_name}' was not found in the document."

    val_str = str(extracted_value).strip()
    
    # 1. Exact Match Check
    if rule_type == "exact_match":
        expected = rule.get("expected", "")
        if val_str.lower() == expected.lower():
            return "match", expected, val_str, "Exact match."
        return "mismatch", expected, val_str, f"Consignee name does not match expected: '{expected}'."
        
    # 2. Prefix Match Check
    elif rule_type == "prefix_match":
        prefixes = rule.get("expected_prefixes", [])
        if any(val_str.startswith(p) for p in prefixes):
            return "match", f"Starts with {prefixes}", val_str, "Prefix match."
        return "mismatch", f"Starts with {prefixes}", val_str, f"HS Code '{val_str}' does not start with expected prefix {prefixes}."
        
    # 3. Allow List Check
    elif rule_type == "allow_list":
        allowed = rule.get("expected", [])
        # Case-insensitive membership check
        if any(val_str.lower() == a.lower() or a.lower() in val_str.lower() for a in allowed):
            return "match", f"One of {allowed}", val_str, "Value in allow-list."
        return "mismatch", f"One of {allowed}", val_str, f"Value '{val_str}' is not in approved list: {allowed}."
        
    # 4. Pattern Match Check (Regex)
    elif rule_type == "pattern_match":
        pattern = rule.get("expected_pattern", "")
        if re.search(pattern, val_str):
            return "match", f"Matches pattern '{pattern}'", val_str, "Regex format matched."
        return "mismatch", f"Matches pattern '{pattern}'", val_str, f"Invoice number does not fit expected format: {pattern}."
        
    # 5. Numeric Limit Check (Max Weight)
    elif rule_type == "numeric_limit":
        max_val = float(rule.get("expected_max", 0))
        found_numeric = clean_weight(val_str)
        if found_numeric is None:
            return "uncertain", f"Numeric value <= {max_val}", val_str, "Unable to parse numeric weight from text."
        if found_numeric <= max_val:
            return "match", f"<= {max_val} kg", f"{found_numeric} kg", f"Weight {found_numeric} kg within acceptable limit of {max_val} kg."
        return "mismatch", f"<= {max_val} kg", f"{found_numeric} kg", f"Weight {found_numeric} kg exceeds maximum limit of {max_val} kg."
        
    return "match", None, val_str, "Default match (No matching rules executed)."

def validate_cross_document_consistency(extracted_data: dict, logs: list[str]) -> dict:
    """Compares core fields across all parsed documents to detect discrepancies.
    
    Returns a dictionary with consistency status and list of discrepancy objects.
    """
    cross_doc_results = {
        "is_consistent": True,
        "discrepancies": []
    }
    
    if len(extracted_data) <= 1:
        return cross_doc_results
        
    logs.append("Validator Agent: Running cross-document consistency checks...")
    cross_fields = ["consignee_name", "hs_code", "gross_weight", "incoterms", "invoice_number"]
    
    for field in cross_fields:
        field_values = {}
        for doc_name, doc_data in extracted_data.items():
            if not isinstance(doc_data, dict):
                continue
            field_data = doc_data.get(field) or {}
            val = field_data.get("value")
            if val is not None and str(val).strip() != "" and str(val).lower() != "null":
                field_values[doc_name] = str(val).strip()
                
        if len(field_values) > 1:
            distinct_values = {}
            for doc, raw_val in field_values.items():
                norm_val = raw_val.lower().strip()
                if field == "gross_weight":
                    cleaned = clean_weight(raw_val)
                    if cleaned is not None:
                        norm_val = f"{cleaned:.2f}"
                elif field == "invoice_number":
                    norm_val = re.sub(r"[^\w]", "", raw_val).lower()
                elif field == "hs_code":
                    norm_val = re.sub(r"[^\d]", "", raw_val)
                    if len(norm_val) >= 4:
                        norm_val = norm_val[:4]
                elif field == "consignee_name":
                    norm_val = re.sub(r"[^\w\s]", "", raw_val).lower().strip()
                    norm_val = norm_val.replace("limited", "ltd").replace("incorporated", "inc").replace("corporation", "corp")
                
                if norm_val not in distinct_values:
                    distinct_values[norm_val] = []
                distinct_values[norm_val].append((doc, raw_val))
            
            if len(distinct_values) > 1:
                cross_doc_results["is_consistent"] = False
                discrepancy_detail = {
                    "field": field,
                    "values": field_values,
                    "reason": f"Discrepancy in '{field.replace('_', ' ')}' across documents: " + 
                              ", ".join(f"'{doc}': {val}" for doc, val in field_values.items())
                }
                cross_doc_results["discrepancies"].append(discrepancy_detail)
                logs.append(f"Validator Agent: Cross-doc discrepancy found on '{field}': {list(field_values.values())}")
                
    return cross_doc_results