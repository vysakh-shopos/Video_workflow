from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


class TransitionType(str, Enum):
    """Type of transition between video clips"""
    CUT = "cut"
    CROSSFADE = "crossfade"


class Transition(BaseModel):
    """Transition configuration between video segments"""
    type: TransitionType = Field(..., description="Type of transition to apply")
    duration: float = Field(
        ..., 
        ge=0.0, 
        le=2.0, 
        description="Duration of transition in seconds (0.0 for cuts, 0.3-1.0 for crossfades)"
    )

    class Config:
        use_enum_values = True


class VideoSegment(BaseModel):
    """Individual video segment in the edit plan"""
    segment_number: int = Field(..., description="Sequential segment number")
    video_url: str = Field(..., description="URL or path to the video clip")
    start_time: Optional[float] = Field(
        None, 
        description="Start time to trim the clip (None = use full clip)"
    )
    end_time: Optional[float] = Field(
        None, 
        description="End time to trim the clip (None = use full clip)"
    )
    transition: Transition = Field(
        ..., 
        description="Transition to apply when entering this segment"
    )
    creative_note: Optional[str] = Field(
        None, 
        description="Creative reasoning for this segment placement"
    )


class EditPlan(BaseModel):
    """Complete AI-generated video editing plan"""
    segments: List[VideoSegment] = Field(
        ..., 
        min_items=1, 
        description="List of video segments with transitions"
    )
    total_estimated_duration: float = Field(
        ..., 
        description="Estimated total duration of the final video in seconds"
    )
    creative_rationale: str = Field(
        ..., 
        description="Overall creative vision and reasoning for the edit"
    )
    pacing_style: str = Field(
        ..., 
        description="Pacing approach (e.g., 'dynamic', 'slow-burn', 'rhythmic')"
    )

