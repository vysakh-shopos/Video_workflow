"""
Centralized settings and environment variable configuration
Loads all environment variables from .env file and provides them as module-level constants
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ============================================
# # AWS S3 Configuration
# # ============================================
# AWS_REGION = os.getenv("AWS_REGION", "")
# AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
# AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
# S3_ASSET_BUCKET = os.getenv("S3_ASSET_BUCKET", "")
# CDN_URL = os.getenv("CDN_URL", "")

# # ============================================
# # Supabase Configuration (Storage/Database - Project B)
# # ============================================
# SUPABASE_URL = os.getenv("SUPABASE_URL")
# SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
# SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
# SUPABASE_STORAGE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "video-copilot-storage")
# SUPABASE_SIGNED_URL_TTL = int(os.getenv("SUPABASE_SIGNED_URL_TTL", "3600"))

# # ============================================
# # Supabase Auth Configuration (Project A)
# # ============================================
# SUPABASE_AUTH_URL = os.getenv("SUPABASE_AUTH_URL")
# SUPABASE_AUTH_ANON_KEY = os.getenv("SUPABASE_AUTH_ANON_KEY")
# SUPABASE_AUTH_SERVICE_ROLE_KEY = os.getenv("SUPABASE_AUTH_SERVICE_ROLE_KEY")

# # ============================================
# # AI API Keys
# # ============================================
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
# REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")
# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
# FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", "")
# IMGBB_API_KEY = os.getenv("IMGBB_API_KEY", "")

# # ============================================
# # Video Generation Settings
# # ============================================
# KLING_MAX_CONCURRENCY = int(os.getenv("KLING_MAX_CONCURRENCY", "2"))

from pydantic import BaseModel



class Settings(BaseModel):
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY")
    REPLICATE_API_TOKEN: str = os.getenv("REPLICATE_API_TOKEN")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY")
    IMGBB_API_KEY: str = os.getenv("IMGBB_API_KEY")
    KLING_MAX_CONCURRENCY: int = os.getenv("KLING_MAX_CONCURRENCY")
    
    AWS_REGION: str = os.getenv("AWS_REGION")
    S3_ASSET_BUCKET: str = os.getenv("S3_ASSET_BUCKET")
    CDN_URL: str = os.getenv("CDN_URL") or ""


settings = Settings()