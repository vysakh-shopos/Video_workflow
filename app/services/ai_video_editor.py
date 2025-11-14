import os
import sys
import time
import tempfile
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from io import BytesIO

import requests
from moviepy import VideoFileClip, CompositeVideoClip, concatenate_videoclips, vfx

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

            # Load video clips
            clips = [VideoFileClip(path) for path in temp_video_paths]
            lg.info(f"Loaded {len(clips)} video clips")

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
                if transition_type == TransitionType.CROSSFADE and i > 0:
                    # Apply crossfade: fade in on current clip, fade out on previous clip
                    lg.info(
                        f"Applying {transition_duration}s crossfade between "
                        f"clip {i} and clip {i+1}"
                    )

                    # Apply fade-in to current clip
                    clip = clip.with_effects([vfx.CrossFadeIn(transition_duration)])

                    # Apply fade-out to previous clip (re-assign in timeline)
                    prev_clip = timeline_clips[-1]
                    timeline_clips[-1] = prev_clip.with_effects([vfx.CrossFadeOut(transition_duration)])

                    # Calculate overlapping start time
                    start_time = current_timeline_end - transition_duration
                    lg.debug(
                        f"Crossfade overlap: previous ends at {current_timeline_end:.2f}s, "
                        f"current starts at {start_time:.2f}s"
                    )

                else:
                    # Hard cut: no overlap
                    start_time = current_timeline_end
                    if i == 0:
                        lg.info(f"First clip starts at {start_time:.2f}s (no fade-in)")
                    else:
                        lg.info(f"Cut transition: clip starts at {start_time:.2f}s")

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
            
            # Get size from first clip
            if timeline_clips:
                size = timeline_clips[0].size
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
    ) -> str:
        """
        Main entry point: Create an AI-driven edit plan and execute it.

        Args:
            video_urls: List of video URLs to stitch together
            output_path: Path for the final output video

        Returns:
            str: Path to the final edited video
        """
        try:
            lg.info(f"Starting AI-driven video stitching for {len(video_urls)} clips")

            # Step 1: Create AI edit plan
            edit_plan = self.create_edit_plan(video_urls)

            # Step 2: Execute the plan
            final_path = self._execute_ai_edit_plan(edit_plan, video_urls, output_path)

            lg.info(f"AI video editing complete! Final video: {final_path}")
            return final_path

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
    final_video_path = ai_video_editor.stitch_videos(video_urls, output_file)

    print(f"\n=== AI Video Editing Complete ===")
    print(f"Final video: {final_video_path}")

