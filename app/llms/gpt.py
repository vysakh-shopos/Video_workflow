import os, sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from typing import  Dict, List, Optional, Union

from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.callbacks import AsyncCallbackHandler
from loguru import logger
from app.config.settings import settings

class GPTHandler:
    def __init__(
        self,
        model_name: str = "gpt-4",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        api_key: Optional[str] = None,
        streaming: bool = False,
        callbacks: Optional[List[AsyncCallbackHandler]] = None,
    ):
       
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.api_key = settings.OPENAI_API_KEY
        self.streaming = streaming
        self.callbacks = callbacks or []

        if not self.api_key:
            logger.error("OpenAI API key not found in environment or parameters")
            raise ValueError("OPENAI_API_KEY not configured")

        # Initialize LangChain ChatOpenAI
        self.llm = self._initialize_llm()
        logger.info(f"Initialized GPTHandler with model: {model_name}")

    def _initialize_llm(self) -> ChatOpenAI:
        """Initialize the LangChain ChatOpenAI instance."""
        llm_params = {
            "model_name": self.model_name,
            "temperature": self.temperature,
            "openai_api_key": self.api_key,
            "streaming": self.streaming,
        }

        if self.max_tokens:
            llm_params["max_tokens"] = self.max_tokens

        if self.callbacks:
            llm_params["callbacks"] = self.callbacks

        return ChatOpenAI(**llm_params)


if __name__ == "__main__":
    gpt = GPTHandler()
    print(gpt.llm.invoke("Hello, how are you?"))