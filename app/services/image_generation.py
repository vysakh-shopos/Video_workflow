import os, sys,time ,asyncio
from pathlib import Path
from typing import Optional
from datetime import datetime

from google.genai import types
from PIL import Image
from io import BytesIO

sys.path.append(str(Path(__file__).parent.parent.parent))

from app.config.settings import settings
from app.llms.naonbana import naonbana_handler
from app.prompts.image_generation import IMAGE_GENERATION_PROMPT
from app.models.script_writer import VideoScript, Frame
from app.models.image_generation import VideoScriptWithImages
from app.utils.video_script_transformer import build_video_script_with_images
from app.utils.get_url import get_url
from app.utils.storage import storage_upload_bytes

from loguru import logger as lg



async def generate_single_image(frame: Frame, scene_number: int, product_url: Optional[str] = None) -> Optional[str]:
    """
    Generate a single image for a frame using the naonbana handler.
    
    Args:
        frame: Frame object containing visual prompt and details
        scene_number: Scene number for logging purposes
        
    Returns:
        Optional[str]: URL of the generated image or None if generation failed
    """
    try:
        # Construct enhanced prompt with frame details
        enhanced_prompt = f"""{IMAGE_GENERATION_PROMPT}

            Visual Description: {frame.visual_prompt}
            Camera Angle: {frame.camera_angle}
            Shot Type: {frame.shot_type}
            Lighting: {frame.lighting}
            Background: {frame.background_details}
            Has Model: {'Yes' if frame.has_model else 'No'}"""

        lg.info(f"Generating image for Scene {scene_number}, Frame {frame.frame_number}")

        contents=[enhanced_prompt]
        if product_url:
            img_bytes = get_url(product_url)
            contents.append("here is the product image:")
            contents.append(types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"))

        config = types.GenerateContentConfig(
        response_modalities=["IMAGE"],
        image_config=types.ImageConfig(aspect_ratio="9:16"))

        
        # Generate image using Gemini's image generation
        response = await asyncio.to_thread(
            naonbana_handler.google_genai.models.generate_content,
            model=naonbana_handler.model,
            contents=contents,
            config=config

        )

        for part in response.candidates[0].content.parts:
            if part.inline_data:
                gen_img = Image.open(BytesIO(part.inline_data.data))
                img_buffer = BytesIO()
                output_format = "png"
                gen_img.save(img_buffer, format=output_format.upper())
                img_bytes = img_buffer.getvalue()
                
                # Create S3 key with timestamp
                timestamp = int(datetime.now().timestamp())
                s3_key = f"{scene_number}-{frame.frame_number}-{timestamp}.{output_format}"
                
                # Upload to S3
                image_url = await storage_upload_bytes(settings.S3_ASSET_BUCKET, s3_key, img_bytes, content_type="image/jpeg")

                return image_url

        return None
    except Exception as e:
        lg.error(f"Error generating image for Scene {scene_number}, Frame {frame.frame_number}: {e}")
        return None


async def generate_images(video_script: VideoScript, product_url: Optional[str] = None) -> VideoScriptWithImages:
    """
    Generate images for all frames in the video script using parallel processing.
    
    Args:
        video_script: VideoScript object containing scenes and frames
        product_url: Optional URL of the product for reference in image generation
        
    Returns:
        VideoScriptWithImages: Enhanced video script with image URLs populated in frames
    """
    try:
        start_time = time.time()
        lg.info(f"Starting image generation for video: {video_script.video_title}")
        
        # Collect all frames and their metadata for processing
        frame_tasks = []
        frame_scene_map = []  # Track which scene each frame belongs to


        for scene in video_script.scenes:
            for frame in scene.frames:
                frame_tasks.append(generate_single_image(frame, scene.scene_number, product_url))
                frame_scene_map.append((scene, frame))
        
        lg.info(f"Generating {len(frame_tasks)} images in parallel...")
        
        # Execute all image generation tasks in parallel
        image_urls = await asyncio.gather(*frame_tasks)
        
        # Build enhanced VideoScript with image URLs using utility function
        video_script_with_images = build_video_script_with_images(
            video_script=video_script,
            image_urls=image_urls,
            frame_scene_map=frame_scene_map
        )
        
        # Count successful generations
        successful_count = sum(1 for url in image_urls if url is not None)
        lg.info(f"Image generation complete: {successful_count}/{len(frame_tasks)} images generated successfully")
        end_time = time.time()
        lg.info(f"Image generation time: {end_time - start_time} seconds")
        return video_script_with_images
        
    except Exception as e:
        lg.error(f"Error in generate_images service: {e}")
        raise


if __name__ == "__main__":
    # Example usage for testing
    from app.services.script_writer import write_script
    
    async def test_generation():
        script = write_script(
            product_category="Skincare",
            product_description="A luxurious vitamin C serum that brightens skin, reduces dark spots, and provides antioxidant protection."
        )
        enhanced_script = await generate_images(script)
        
        # Print results
        for scene in enhanced_script.scenes:
            print(f"\nScene {scene.scene_number}: {scene.scene_title}")
            for frame in scene.frames:
                print(f"  Frame {frame.frame_number}: {frame.image_url}")
    
    asyncio.run(test_generation())
