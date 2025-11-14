from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from enum import Enum


class CameraAngle(str, Enum):
    """Camera angle options for video frames"""
    EXTREME_CLOSEUP = "extreme_closeup"
    CLOSEUP = "closeup"
    MEDIUM_SHOT = "medium_shot"
    FULL_SHOT = "full_shot"
    WIDE_SHOT = "wide_shot"
    OVERHEAD = "overhead"
    LOW_ANGLE = "low_angle"
    HIGH_ANGLE = "high_angle"
    DUTCH_ANGLE = "dutch_angle"
    POV = "pov"
    OVER_SHOULDER = "over_shoulder"


class ShotType(str, Enum):
    """Type of shot composition"""
    STATIC = "static"
    PAN = "pan"
    TILT = "tilt"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"
    DOLLY = "dolly"
    TRACKING = "tracking"
    CRANE = "crane"
    HANDHELD = "handheld"
    STEADICAM = "steadicam"


class Frame(BaseModel):
    """Individual frame/clip in a scene"""
    frame_number: int = Field(..., description="Sequential frame number")
    visual_prompt: str = Field(..., min_length=20, description="Detailed visual description for AI video generation")
    camera_angle: CameraAngle = Field(..., description="Camera angle for this frame")
    shot_type: ShotType = Field(..., description="Type of camera movement")
    has_model: bool = Field(..., description="Whether this frame includes a human model")
    lighting: str = Field(..., description="Lighting setup (e.g., 'soft natural light', 'dramatic backlight')")
    background_details: str = Field(..., description="Background description and elements")


    
    class Config:
        use_enum_values = True


class Scene(BaseModel):
    """A scene containing multiple frames"""
    scene_number: int = Field(..., description="Sequential scene number")
    scene_title: str = Field(..., description="Descriptive title for this scene")
    scene_purpose: str = Field(..., description="What this scene aims to communicate")
    setting: str = Field(..., description="Location/environment description")
    mood: str = Field(..., description="Emotional tone of the scene")
    frames: List[Frame] = Field(..., min_items=1, description="List of frames in this scene", min_length=2, max_length=3)


class VideoScript(BaseModel):
    """Complete video script structure"""
    product_category: str = Field(..., description="Category of the product")
    product_name: str = Field(..., description="Name of the product")
    video_title: str = Field(..., description="Compelling title for the video")
    video_hook: str = Field(..., description="Opening hook to grab attention in first 3 seconds")
    target_audience: str = Field(..., description="Primary audience for this video")
    video_objective: str = Field(..., description="Main goal of the video")
    scenes: List[Scene] = Field(..., min_items=3, description="List of scenes in the video", min_length=3, max_length=4)
