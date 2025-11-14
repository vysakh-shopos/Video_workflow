

from langchain_anthropic import ChatAnthropic

from app.config.settings import settings

class ClaudeHandler:
    def __init__(self):
        self.llm = ChatAnthropic(
            api_key=settings.ANTHROPIC_API_KEY,
            model="claude-sonnet-4-20250514",
            temperature=0.7
        )

claude_handler = ClaudeHandler()
