

def decide_lane(validation_results: dict, cross_doc_results: dict | None = None) -> str:
    """Deterministically selects the next workflow lane:
    - `amendment_request` : Cross-document discrepancies requiring external document reissue from shipper.
    - `flag_review`      : Policy/rule violations or low confidence requiring internal compliance auditor sign-off.
    - `auto_approve`     : Fully compliant across all individual rules and multi-document consistency checks.
    """
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

    has_cross_doc_discrepancy = bool(cross_doc_results and not cross_doc_results.get("is_consistent", True))
    has_rule_mismatch = any(res.get("result") == "mismatch" for res in all_individual_results)
    has_uncertainty = any(res.get("result") == "uncertain" for res in all_individual_results)

    # 1. Cross-document discrepancies require amended documents from shipper/carrier
    if has_cross_doc_discrepancy:
        return "amendment_request"

    # 2. Rule violations or extraction uncertainty require auditor review
    if has_rule_mismatch or has_uncertainty:
        return "flag_review"

    # 3. Fully compliant
    return "auto_approve"