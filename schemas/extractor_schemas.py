from typing import List, Optional
from pydantic import BaseModel, Field

class ExtractedField(BaseModel):
    value: Optional[str] = Field(description="The extracted value of the field. Return null if not found.")
    confidence: float = Field(description="Confidence score from 0.0 to 1.0. 0.9+ for clear/legible, 0.5-0.8 for partial/inferred, <0.5 for guessed/absent.")
    source_snippet: Optional[str] = Field(description="The exact snippet of text from the document where this field was found. Return null if not found.")

class TradeDocumentExtraction(BaseModel):
    consignee_name: ExtractedField = Field(description="Name of the consignee (receiving party's company name).")
    hs_code: ExtractedField = Field(description="Harmonized System tariff code (e.g. 8708.29.90).")
    port_of_loading: ExtractedField = Field(description="The port where cargo is loaded onto the vessel (origin).")
    port_of_discharge: ExtractedField = Field(description="The destination port where cargo is unloaded (destination).")
    incoterms: ExtractedField = Field(description="Incoterms (e.g. FOB, CIF, EXW).")
    description_of_goods: ExtractedField = Field(description="Detailed description of the shipped goods.")
    gross_weight: ExtractedField = Field(description="Total gross weight including packaging, with unit (e.g. '1250 KG').")
    invoice_number: ExtractedField = Field(description="The unique invoice identifier.")
    extraction_warnings: List[str] = Field(description="Document-level warnings.")
