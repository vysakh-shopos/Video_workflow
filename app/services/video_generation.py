import os
import sys
import time
import asyncio
from pathlib import Path
from typing import Optional, List
from datetime import datetime
from io import BytesIO

import requests


sys.path.append(str(Path(__file__).parent.parent.parent))
from app.utils.get_url import validate_url

from app.config.settings import settings
from app.llms._kling import kling_handler
from app.models.image_generation import VideoScriptWithImages, FrameWithImage
from app.models.video_generation import VideoGenerationResult
from app.utils.storage import storage_upload_bytes

from loguru import logger as lg


async def generate_single_video(
    frame_with_image: FrameWithImage, scene_number: int
) -> Optional[str]:
    """
    Generate a single video clip for a frame using Kling AI via Replicate.
    
    Args:
        frame_with_image: FrameWithImage object containing image URL and frame details
        scene_number: Scene number for logging purposes
        
    Returns:
        Optional[str]: URL of the generated video or None if generation failed
    """
    try:
        if not frame_with_image.image_url:
            lg.warning(
                f"No image URL for Scene {scene_number}, "
                f"Frame {frame_with_image.frame_number}. Skipping video generation."
            )
            return None

        # Construct enhanced prompt with frame details
        enhanced_prompt = f"""{frame_with_image.visual_prompt}

            Camera Angle: {frame_with_image.camera_angle}
            Shot Type: {frame_with_image.shot_type}
            Lighting: {frame_with_image.lighting}
            Background: {frame_with_image.background_details}"""

        lg.info(
            f"Generating video for Scene {scene_number}, "
            f"Frame {frame_with_image.frame_number}"
        )

        input_data = {
            "prompt": enhanced_prompt,
            "start_image": frame_with_image.image_url,
            }
        output = await asyncio.to_thread(
            kling_handler.replicate.run,
            kling_handler.model,
            input=input_data,
        )

        # The output is typically a URL or list of URLs
        video_url = output if isinstance(output, str) else output.url

        lg.info(
            f"Kling generated video URL for Scene {scene_number}, "
            f"Frame {frame_with_image.frame_number}: {video_url}"
        )

        # Download the video from Replicate
        response = await asyncio.to_thread(requests.get, video_url)
        response.raise_for_status()
        video_bytes = response.content

        # Create S3 key with timestamp
        timestamp = int(datetime.now().timestamp())
        s3_key = f"videos/{scene_number}-{frame_with_image.frame_number}-{timestamp}.mp4"

        # Upload to S3
        uploaded_url = await storage_upload_bytes(
            settings.S3_ASSET_BUCKET, s3_key, video_bytes, content_type="video/mp4"
        )

        lg.info(
            f"Video uploaded to S3 for Scene {scene_number}, "
            f"Frame {frame_with_image.frame_number}: {uploaded_url}"
        )

        return uploaded_url

    except Exception as e:
        lg.error(
            f"Error generating video for Scene {scene_number}, "
            f"Frame {frame_with_image.frame_number}: {e}"
        )
        return None


async def generate_videos(
    video_script_with_images: VideoScriptWithImages,
) -> List[Optional[str]]:
    """
    Generate video clips for all frames in the video script using parallel processing.
    
    Args:
        video_script_with_images: VideoScriptWithImages object with image URLs populated
        
    Returns:
        List[Optional[str]]: List of video URLs (one per frame), None for failed generations
    """
    try:
        start_time = time.time()
        lg.info(f"Starting video generation for: {video_script_with_images.video_title}")

        video_tasks = []
        frame_metadata = []  # Track scene and frame info


        for scene in video_script_with_images.scenes:
            for frame in scene.frames:
                video_tasks.append(generate_single_video(frame, scene.scene_number))
                frame_metadata.append(
                    {
                        "scene_number": scene.scene_number,
                        "frame_number": frame.frame_number,
                        "scene_title": scene.scene_title,
                    }
                )

        lg.info(f"Generating {len(video_tasks)} videos in parallel...")

        # Execute all video generation tasks in parallel
        video_urls = await asyncio.gather(*video_tasks)

        # Count successful generations
        successful_count = sum(1 for url in video_urls if url is not None)
        failed_count = len(video_urls) - successful_count

        lg.info(
            f"Video generation complete: {successful_count}/{len(video_tasks)} "
            f"videos generated successfully, {failed_count} failed"
        )

        end_time = time.time()
        lg.info(f"Video generation time: {end_time - start_time:.2f} seconds")

        return video_urls

    except Exception as e:
        lg.error(f"Error in generate_videos service: {e}")
        raise


if __name__ == "__main__":
    # Example usage for testing
    from app.services.script_writer import write_script
    from app.services.image_generation import generate_images

    async def test_video_generation():
        # Generate a script
        script = write_script(
            product_category="Skincare",
            product_description=(
                "A luxurious vitamin C serum that brightens skin, "
                "reduces dark spots, and provides antioxidant protection."
            ),
        )

        # Generate images for the script
        lg.info("Generating images...")
        script_with_images = await generate_images(script)

        # Generate videos from images
        lg.info("Generating videos...")
        video_urls = await generate_videos(script_with_images)

        # Print results
        print("\n=== Video Generation Results ===")
        for i, url in enumerate(video_urls):
            if url:
                print(f"Video {i + 1}: {url}")
            else:
                print(f"Video {i + 1}: FAILED")

    asyncio.run(test_video_generation())

