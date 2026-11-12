from pydantic import BaseModel, Field

class RouterResponse(BaseModel):
    reasoning: str = Field(description="A naturally written, human-friendly explanation of why this specific routing lane was chosen, referencing the fields involved.")
    amendment_draft: str = Field(description="If the decision is 'amendment_request', write a professional, specific email draft to the supplier listing all discrepancies (Field, Found, Expected). If the decision is 'flag_review', write brief inspect notes for the operator. If 'auto_approve', write a short confirmation note.")
