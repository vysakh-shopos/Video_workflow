from pydantic import BaseModel, Field
from typing import List, Optional

from app.models.image_generation import FrameWithImage


class FrameWithVideo(FrameWithImage):
    """Frame with generated image and video URL"""
    video_url: Optional[str] = Field(None, description="URL of the generated video for this frame")


class VideoGenerationResult(BaseModel):
    """Result of video generation containing list of video URLs with metadata"""
    video_urls: List[Optional[str]] = Field(..., description="List of generated video URLs (one per frame)")
    total_frames: int = Field(..., description="Total number of frames processed")
    successful_count: int = Field(..., description="Number of successfully generated videos")
    failed_count: int = Field(..., description="Number of failed video generations")

