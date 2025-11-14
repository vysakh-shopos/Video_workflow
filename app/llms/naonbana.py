
from google import genai
from app.config.settings import settings


class NaonbanaHandler:
    def __init__(self):
        self.google_genai = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model = "gemini-2.5-flash-image"


naonbana_handler = NaonbanaHandler()
