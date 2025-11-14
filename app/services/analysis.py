import os, sys,time 
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from langchain_core.messages import HumanMessage, SystemMessage

from app.llms.gpt import GPTHandler
from app.prompts.analyser import system_prompt_analyser
from app.models.analyser import CreativeAnalysisResponse

from loguru import logger as lg

def analyze_product_image(image_url: str) -> str:
    """
    Analyze an image from a URL and identify the product with its attributes.
    
    Args:
        image_url: URL of the image to analyze
        
    Returns:
        Description of the product (e.g., "black shoes", "red t-shirt")
    """
    start_time = time.time()
    llm_gpt = GPTHandler(model_name="gpt-4o", temperature=0.3)
    llm_structured_output = llm_gpt.llm.with_structured_output(CreativeAnalysisResponse)
    
    messages = [
        SystemMessage(content=system_prompt_analyser),
        HumanMessage(
            content=[
                {"type": "text", "text": "Analyze this product image:"},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]
        )
    ]
    
    response = llm_structured_output.invoke(messages)
    end_time = time.time()
    lg.info(f"Analysis time: {end_time - start_time} seconds")
    response=response.model_dump()
    return response


if __name__ == "__main__":
    # Example usage
    test_url = "https://dev.cdn.pro.corp.shopos.ai/1762085261_additional_pose_three_quarter_profile_top_wear_1_09a735ce_9def_437a_82f2_dfd7860eedbe.png"
    description = analyze_product_image(test_url)
    print(f"Product: {description}")

