from pydantic import BaseModel, Field
from typing import List, Optional

from app.models.script_writer import Frame, CameraAngle, ShotType


class FrameWithImage(Frame):
    """Frame with generated image URL"""
    image_url: Optional[str] = Field(None, description="URL of the generated image for this frame")


class SceneWithImages(BaseModel):
    """Scene with frames containing image URLs"""
    scene_number: int = Field(..., description="Sequential scene number")
    scene_title: str = Field(..., description="Descriptive title for this scene")
    scene_purpose: str = Field(..., description="What this scene aims to communicate")
    setting: str = Field(..., description="Location/environment description")
    mood: str = Field(..., description="Emotional tone of the scene")
    frames: List[FrameWithImage] = Field(..., min_items=1, description="List of frames with images in this scene")


class VideoScriptWithImages(BaseModel):
    """VideoScript enhanced with generated images"""
    product_category: str = Field(..., description="Category of the product")
    product_name: str = Field(..., description="Name of the product")
    video_title: str = Field(..., description="Compelling title for the video")
    video_hook: str = Field(..., description="Opening hook to grab attention in first 3 seconds")
    target_audience: str = Field(..., description="Primary audience for this video")
    video_objective: str = Field(..., description="Main goal of the video")
    scenes: List[SceneWithImages] = Field(..., min_items=3, description="List of scenes with images in the video")

