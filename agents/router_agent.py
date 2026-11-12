

def decide_lane(validation_results: dict, cross_doc_results: dict | None = None) -> str:
    """Deterministically selects the next workflow lane."""
    # Detect if validation_results is nested (filenames map to dicts of fields)
    is_nested = False
    if validation_results:
        first_val = list(validation_results.values())[0]
        if isinstance(first_val, dict) and any(isinstance(v, dict) and "result" in v for v in first_val.values()):
            is_nested = True
            
    # Flatten validation results
    all_individual_results = []
    if is_nested:
        for doc_res in validation_results.values():
            all_individual_results.extend(doc_res.values())
    else:
        all_individual_results = list(validation_results.values())
        
    # 1. Any individual field mismatch -> amendment_request
    if any(res.get("result") == "mismatch" for res in all_individual_results):
        return "amendment_request"
        
    # 2. Cross-document consistency failure -> amendment_request
    if cross_doc_results and not cross_doc_results.get("is_consistent", True):
        return "amendment_request"
        
    # 3. Any individual field uncertainty -> flag_review
    if any(res.get("result") == "uncertain" for res in all_individual_results):
        return "flag_review"
        
    # 4. Otherwise -> auto_approve
    return "auto_approve"