import os, sys, time
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.llms._claude import claude_handler

from app.prompts.script_writer import VIDEO_SCRIPT_PROMPT
from app.models.script_writer import VideoScript
from loguru import logger as lg


def write_script(product_category: str, product_description: str) -> VideoScript:
    try:
        start_time = time.time()
        llm_structured_output = claude_handler.llm.with_structured_output(VideoScript)
        messages = [
            SystemMessage(content=VIDEO_SCRIPT_PROMPT),
            HumanMessage(content=f"Product Category: {product_category}\nProduct Description: {product_description}")
        ]
        response = llm_structured_output.invoke(messages)
        end_time = time.time()
        lg.info(f"Script writing time: {end_time - start_time} seconds")
        return response
    except Exception as e:
        lg.error(f"Error writing script: {e}")
        


if __name__ == "__main__":
    write_script(product_category="Skincare", product_description="A luxurious vitamin C serum that brightens skin, reduces dark spots, and provides antioxidant protection. Features 15% pure L-ascorbic acid in a stable, fast-absorbing formula.")