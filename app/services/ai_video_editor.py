import os
import sys
import time
import tempfile
import asyncio
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime
from io import BytesIO

import requests
from moviepy import VideoFileClip, CompositeVideoClip, concatenate_videoclips, vfx, ColorClip

sys.path.append(str(Path(__file__).parent.parent.parent))

from app.config.settings import settings
from app.llms._claude import claude_handler
from app.prompts.ai_video_editor import CREATIVE_DIRECTOR_PROMPT
from app.models.ai_video_editor import EditPlan, VideoSegment, TransitionType
from app.utils.storage import storage_upload_bytes
from loguru import logger as lg


class AIVideoEditor:
    """
    AI-powered video editor that uses Claude to intelligently decide transitions
    and execute professional video edits with cuts and crossfades.
    """

    def __init__(self):
        self.llm = claude_handler.llm

    def _upload_video_to_s3(self, video_path: str) -> Optional[str]:
        """
        Upload a video file to S3 storage.

        Args:
            video_path: Local path to the video file

        Returns:
            str: S3 URL of the uploaded video, or None if upload failed
        """
        try:
            lg.info(f"Uploading video to S3: {video_path}")
            
            # Read the video file as bytes
            with open(video_path, "rb") as f:
                video_bytes = f.read()
            
            # Generate S3 key with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = Path(video_path).name
            s3_key = f"ai_edited_videos/{timestamp}_{filename}"
            
            # Upload to S3 (storage_upload_bytes is async, so we need to run it)
            lg.info(f"Uploading {len(video_bytes)} bytes to S3 key: {s3_key}")
            s3_url = asyncio.run(
                storage_upload_bytes(
                    bucket=settings.S3_ASSET_BUCKET,
                    key=s3_key,
                    data=video_bytes,
                    content_type="video/mp4"
                )
            )
            
            if s3_url:
                lg.info(f"Video successfully uploaded to S3: {s3_url}")
            else:
                lg.warning("S3 upload returned None - upload may have failed")
            
            return s3_url
            
        except Exception as e:
            lg.error(f"Error uploading video to S3: {e}")
            return None

    def create_edit_plan(self, video_urls: List[str]) -> EditPlan:
        """
        Use Claude as a Creative Director to analyze video clips and create an edit plan.

        Args:
            video_urls: List of URLs to video clips

        Returns:
            EditPlan: AI-generated editing plan with transitions
        """
        try:
            lg.info(f"Creating AI edit plan for {len(video_urls)} video clips...")
            start_time = time.time()

            # Prepare the input for the AI
            video_list = "\n".join([f"{i+1}. {url}" for i, url in enumerate(video_urls)])
            human_message = f"""I have {len(video_urls)} video clips that need to be edited together into a cohesive final video.

VIDEO CLIPS:
{video_list}

Please analyze these clips and create a professional editing plan that determines the optimal transitions between each clip. Consider pacing, narrative flow, and visual continuity."""

            # Use structured output with the EditPlan model
            llm_structured = self.llm.with_structured_output(EditPlan)

            from langchain_core.messages import SystemMessage, HumanMessage

            messages = [
                SystemMessage(content=CREATIVE_DIRECTOR_PROMPT),
                HumanMessage(content=human_message),
            ]

            response = llm_structured.invoke(messages)

            end_time = time.time()
            lg.info(f"AI edit plan created in {end_time - start_time:.2f} seconds")
            lg.info(f"Creative rationale: {response.creative_rationale}")
            lg.info(f"Pacing style: {response.pacing_style}")

            return response

        except Exception as e:
            lg.error(f"Error creating AI edit plan: {e}")
            raise

    def _download_video(self, url: str, temp_dir: str, index: int) -> str:
        """
        Download a video from URL to a temporary file.

        Args:
            url: Video URL
            temp_dir: Temporary directory path
            index: Video index for naming

        Returns:
            str: Path to downloaded video file
        """
        try:
            lg.info(f"Downloading video {index + 1} from {url[:60]}...")
            response = requests.get(url, timeout=60)
            response.raise_for_status()

            # Save to temp file
            temp_path = os.path.join(temp_dir, f"clip_{index}.mp4")
            with open(temp_path, "wb") as f:
                f.write(response.content)

            lg.info(f"Video {index + 1} downloaded successfully")
            return temp_path

        except Exception as e:
            lg.error(f"Error downloading video {index + 1}: {e}")
            raise

    def _execute_ai_edit_plan(
        self, edit_plan: EditPlan, video_urls: List[str], output_path: str
    ) -> str:
        """
        Execute the AI-generated edit plan by applying transitions and compositing clips.

        Args:
            edit_plan: The EditPlan from the AI
            video_urls: List of video URLs corresponding to segments
            output_path: Path for the final output video

        Returns:
            str: Path to the final edited video
        """
        try:
            lg.info("Executing AI edit plan...")
            start_time = time.time()

            # Create temporary directory for downloads
            temp_dir = tempfile.mkdtemp()
            lg.info(f"Using temporary directory: {temp_dir}")

            # Download all videos
            temp_video_paths = []
            for i, url in enumerate(video_urls):
                temp_path = self._download_video(url, temp_dir, i)
                temp_video_paths.append(temp_path)

            # Load video clips with validation
            clips = []
            for i, path in enumerate(temp_video_paths):
                try:
                    clip = VideoFileClip(path)
                    # Validate clip has valid dimensions
                    if not clip.size or clip.size[0] <= 0 or clip.size[1] <= 0:
                        lg.error(f"Clip {i} has invalid dimensions: {clip.size}")
                        clip.close()
                        raise ValueError(f"Clip {i} from {path} has invalid dimensions: {clip.size}")
                    clips.append(clip)
                    lg.info(f"Loaded clip {i}: size={clip.size}, duration={clip.duration:.2f}s")
                except Exception as e:
                    lg.error(f"Error loading clip {i} from {path}: {e}")
                    raise
            
            lg.info(f"Loaded {len(clips)} video clips")

            # Validate and normalize clip dimensions
            if not clips:
                raise ValueError("No clips loaded")
            
            # Find the first valid clip size to use as reference
            reference_size = None
            for clip in clips:
                if clip.size and clip.size[0] > 0 and clip.size[1] > 0:
                    reference_size = clip.size
                    lg.info(f"Using reference size: {reference_size}")
                    break
            
            if not reference_size:
                raise ValueError("No valid clip dimensions found")
            
            # Resize all clips to match reference size
            normalized_clips = []
            for i, clip in enumerate(clips):
                if clip.size != reference_size:
                    lg.info(f"Resizing clip {i} from {clip.size} to {reference_size}")
                    clip = clip.with_effects([vfx.Resize(reference_size)])
                normalized_clips.append(clip)
            clips = normalized_clips

            # Process segments with transition-aware logic
            timeline_clips = []
            current_timeline_end = 0.0

            for i, segment in enumerate(edit_plan.segments):
                if i >= len(clips):
                    lg.warning(f"Segment {i} exceeds available clips. Skipping.")
                    break

                clip = clips[i]
                lg.info(
                    f"Processing segment {segment.segment_number}: "
                    f"Duration={clip.duration:.2f}s, Transition={segment.transition.type}"
                )

                # Get transition info with safe defaults
                transition = segment.transition
                transition_type = transition.type
                transition_duration = transition.duration

                # Apply transition effects based on type
                # ═══════════════════════════════════════════════════════════════
                # CORE TRANSITIONS
                # ═══════════════════════════════════════════════════════════════
                
                if transition_type == TransitionType.CUT:
                    # Hard cut: no overlap
                    start_time = current_timeline_end
                    if i == 0:
                        lg.info(f"First clip starts at {start_time:.2f}s (hard cut)")
                    else:
                        lg.info(f"Cut transition: clip starts at {start_time:.2f}s")
                
                elif transition_type == TransitionType.CROSSFADE and i > 0:
                    # Apply crossfade: fade in on current clip, fade out on previous clip
                    lg.info(
                        f"Applying {transition_duration}s crossfade between "
                        f"clip {i} and clip {i+1}"
                    )
                    clip = clip.with_effects([vfx.CrossFadeIn(transition_duration)])
                    prev_clip = timeline_clips[-1]
                    timeline_clips[-1] = prev_clip.with_effects([vfx.CrossFadeOut(transition_duration)])
                    start_time = current_timeline_end - transition_duration
                
                # ═══════════════════════════════════════════════════════════════
                # FADE TRANSITIONS
                # ═══════════════════════════════════════════════════════════════
                
                elif transition_type == TransitionType.FADE_IN:
                    # Fade from black at the start
                    lg.info(f"Applying {transition_duration}s fade in from black")
                    clip = clip.with_effects([vfx.FadeIn(transition_duration)])
                    start_time = current_timeline_end
                
                elif transition_type == TransitionType.FADE_OUT and i > 0:
                    # Fade to black at the end of previous clip
                    lg.info(f"Applying {transition_duration}s fade out to black")
                    prev_clip = timeline_clips[-1]
                    timeline_clips[-1] = prev_clip.with_effects([vfx.FadeOut(transition_duration)])
                    start_time = current_timeline_end
                
                elif transition_type == TransitionType.FADE_THROUGH_BLACK and i > 0:
                    # Fade out to black, then fade in from black
                    lg.info(f"Applying {transition_duration}s fade through black")
                    half_duration = transition_duration / 2
                    
                    # Apply fade out to previous clip
                    prev_clip = timeline_clips[-1]
                    timeline_clips[-1] = prev_clip.with_effects([vfx.FadeOut(half_duration)])
                    
                    # Apply fade in to current clip
                    clip = clip.with_effects([vfx.FadeIn(half_duration)])
                    
                    # Add gap for black frame
                    start_time = current_timeline_end + half_duration
                
                elif transition_type == TransitionType.FADE_THROUGH_WHITE and i > 0:
                    # Fade out to white, then fade in from white
                    lg.info(f"Applying {transition_duration}s fade through white")
                    half_duration = transition_duration / 2
                    
                    # Apply fade out to previous clip (we'll simulate white by inverting fade logic)
                    prev_clip = timeline_clips[-1]
                    timeline_clips[-1] = prev_clip.with_effects([vfx.FadeOut(half_duration)])
                    
                    # Create white flash clip using reference size
                    white_clip = ColorClip(
                        size=reference_size, 
                        color=(255, 255, 255), 
                        duration=half_duration
                    ).with_start(current_timeline_end)
                    timeline_clips.append(white_clip)
                    
                    # Apply fade in to current clip
                    clip = clip.with_effects([vfx.FadeIn(half_duration)])
                    start_time = current_timeline_end + half_duration
                
                # ═══════════════════════════════════════════════════════════════
                # SLIDE TRANSITIONS
                # ═══════════════════════════════════════════════════════════════
                
                elif transition_type == TransitionType.SLIDE_IN_LEFT:
                    lg.info(f"Applying {transition_duration}s slide in from left")
                    clip = clip.with_effects([vfx.SlideIn(transition_duration, 'left')])
                    start_time = current_timeline_end
                
                elif transition_type == TransitionType.SLIDE_IN_RIGHT:
                    lg.info(f"Applying {transition_duration}s slide in from right")
                    clip = clip.with_effects([vfx.SlideIn(transition_duration, 'right')])
                    start_time = current_timeline_end
                
                elif transition_type == TransitionType.SLIDE_IN_TOP:
                    lg.info(f"Applying {transition_duration}s slide in from top")
                    clip = clip.with_effects([vfx.SlideIn(transition_duration, 'top')])
                    start_time = current_timeline_end
                
                elif transition_type == TransitionType.SLIDE_IN_BOTTOM:
                    lg.info(f"Applying {transition_duration}s slide in from bottom")
                    clip = clip.with_effects([vfx.SlideIn(transition_duration, 'bottom')])
                    start_time = current_timeline_end
                
                # ═══════════════════════════════════════════════════════════════
                # ZOOM TRANSITIONS
                # ═══════════════════════════════════════════════════════════════
                
                elif transition_type == TransitionType.ZOOM_IN and i > 0:
                    # Zoom into previous clip while fading in current clip
                    lg.info(f"Applying {transition_duration}s zoom in transition")
                    
                    # Apply zoom + fade to previous clip
                    # Use resize with fixed scale (1.3x zoom) then resize back to reference
                    prev_clip = timeline_clips[-1]
                    prev_clip_zoomed = prev_clip.with_effects([
                        vfx.Resize(1.3),  # Fixed 1.3x zoom
                        vfx.CrossFadeOut(transition_duration)
                    ])
                    # Ensure it maintains reference size (crop if needed)
                    if prev_clip_zoomed.size != reference_size:
                        prev_clip_zoomed = prev_clip_zoomed.with_effects([vfx.Resize(reference_size)])
                    timeline_clips[-1] = prev_clip_zoomed
                    
                    # Fade in current clip
                    clip = clip.with_effects([vfx.CrossFadeIn(transition_duration)])
                    start_time = current_timeline_end - transition_duration
                
                elif transition_type == TransitionType.ZOOM_OUT and i > 0:
                    # Zoom out of previous clip while fading in current clip
                    lg.info(f"Applying {transition_duration}s zoom out transition")
                    
                    # Apply zoom + fade to previous clip
                    # Use resize with fixed scale (0.8x zoom out) then resize back to reference
                    prev_clip = timeline_clips[-1]
                    prev_clip_zoomed = prev_clip.with_effects([
                        vfx.Resize(0.8),  # Fixed 0.8x zoom out
                        vfx.CrossFadeOut(transition_duration)
                    ])
                    # Ensure it maintains reference size
                    if prev_clip_zoomed.size != reference_size:
                        prev_clip_zoomed = prev_clip_zoomed.with_effects([vfx.Resize(reference_size)])
                    timeline_clips[-1] = prev_clip_zoomed
                    
                    # Fade in current clip
                    clip = clip.with_effects([vfx.CrossFadeIn(transition_duration)])
                    start_time = current_timeline_end - transition_duration
                
                else:
                    # Fallback: treat as cut
                    lg.warning(f"Unknown or unsupported transition type: {transition_type}. Using cut.")
                    start_time = current_timeline_end

                # Set the clip's start time on the timeline
                clip = clip.with_start(start_time)

                # Update timeline position
                current_timeline_end = start_time + clip.duration
                lg.debug(f"Timeline now extends to {current_timeline_end:.2f}s")

                # Add to timeline
                timeline_clips.append(clip)

                # Log creative note if available
                if segment.creative_note:
                    lg.debug(f"Creative note: {segment.creative_note}")

            # Composite all clips with proper timing and overlaps
            lg.info(f"Compositing {len(timeline_clips)} clips...")
            
            # Validate all clips have matching dimensions before compositing
            if timeline_clips:
                # Check and fix any size mismatches
                for i, clip in enumerate(timeline_clips):
                    if not clip.size or clip.size[0] == 0 or clip.size[1] == 0:
                        lg.error(f"Clip {i} has invalid size: {clip.size}")
                        raise ValueError(f"Clip {i} has invalid dimensions: {clip.size}")
                    if clip.size != reference_size:
                        lg.warning(f"Clip {i} size mismatch: {clip.size} != {reference_size}. Resizing...")
                        timeline_clips[i] = clip.with_effects([vfx.Resize(reference_size)])
                
                size = reference_size
                lg.info(f"Compositing with size: {size}")
                final_video = CompositeVideoClip(timeline_clips, size=size)
                
                lg.info(f"Final video duration: {final_video.duration:.2f}s")
                lg.info(f"Writing final video to {output_path}...")

                # Write the final video
                final_video.write_videofile(
                    output_path,
                    codec="libx264",
                    audio_codec="aac",
                    fps=24,
                    preset="medium",
                    threads=4,
                )

                # Close all clips to free resources
                for clip in clips:
                    clip.close()
                final_video.close()

                # Clean up temp files
                lg.info("Cleaning up temporary files...")
                for temp_path in temp_video_paths:
                    try:
                        os.remove(temp_path)
                    except Exception as e:
                        lg.warning(f"Could not remove temp file {temp_path}: {e}")

                try:
                    os.rmdir(temp_dir)
                except Exception as e:
                    lg.warning(f"Could not remove temp directory {temp_dir}: {e}")

                end_time = time.time()
                lg.info(
                    f"Video editing complete in {end_time - start_time:.2f} seconds"
                )

                return output_path
            else:
                raise ValueError("No clips to composite")

        except Exception as e:
            lg.error(f"Error executing AI edit plan: {e}")
            raise

    def stitch_videos(
        self, video_urls: List[str], output_path: str = "final_edit.mp4"
    ) -> Dict[str, Optional[str]]:
        """
        Main entry point: Create an AI-driven edit plan and execute it.

        Args:
            video_urls: List of video URLs to stitch together
            output_path: Path for the final output video

        Returns:
            Dict containing:
                - local_path: Local file path to the final edited video
                - s3_url: S3 URL of the uploaded video (None if upload fails)
        """
        try:
            lg.info(f"Starting AI-driven video stitching for {len(video_urls)} clips")

            # Step 1: Create AI edit plan
            edit_plan = self.create_edit_plan(video_urls)

            # Step 2: Execute the plan
            final_path = self._execute_ai_edit_plan(edit_plan, video_urls, output_path)

            # Step 3: Upload to S3
            s3_url = self._upload_video_to_s3(final_path)

            result = {
                "local_path": final_path,
                "s3_url": s3_url
            }

            lg.info(f"AI video editing complete! Local: {final_path}, S3: {s3_url}")
            return result

        except Exception as e:
            lg.error(f"Error in AI video stitching: {e}")
            raise


# Singleton instance
ai_video_editor = AIVideoEditor()


if __name__ == "__main__":
    # Example usage for testing
    import json

    # Load video URLs from the JSON file
    with open("video_urls.json", "r") as f:
        video_urls = json.load(f)

    lg.info(f"Loaded {len(video_urls)} video URLs")

    # Stitch videos with AI-driven transitions
    output_file = "ai_edited_video.mp4"
    result = ai_video_editor.stitch_videos(video_urls, output_file)

    print(f"\n=== AI Video Editing Complete ===")
    print(f"Local video: {result['local_path']}")
    print(f"S3 URL: {result['s3_url']}")

