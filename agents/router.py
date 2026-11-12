
def decide_lane(validation_results: dict) -> str:
    """Deterministically selects the next workflow lane."""
    # Check if there is even one mismatch -> go to amendment draft
    if any(res.get("result") == "mismatch" for res in validation_results.values()):
        return "amendment_request"
        
    # Check if there is any uncertainty -> flag for human review
    if any(res.get("result") == "uncertain" for res in validation_results.values()):
        return "flag_review"
        
    # Everything is matching -> auto-approve
    return "auto_approve"