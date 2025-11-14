import replicate

from app.config.settings import settings

class KlingHandler:
    def __init__(self):
        self.replicate = replicate.Client(settings.REPLICATE_API_TOKEN)
        self.model = "kwaivgi/kling-v2.1"

kling_handler = KlingHandler()
