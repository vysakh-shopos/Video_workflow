from pydantic import BaseModel

class CreativeAnalysisResponse(BaseModel):
    product_category: str
    product_description: str
