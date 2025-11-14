"""
Utility functions for transforming VideoScript objects
"""

from typing import List, Tuple
from app.models.script_writer import VideoScript, Frame, Scene
from app.models.image_generation import VideoScriptWithImages, SceneWithImages, FrameWithImage
from loguru import logger as lg

def build_video_script_with_images(
    video_script: VideoScript,
    image_urls: List[str],
    frame_scene_map: List[Tuple[Scene, Frame]]
) -> VideoScriptWithImages:
    try:


        scenes_with_images = []
        
        for scene in video_script.scenes:
            frames_with_images = []
            
            for frame in scene.frames:
                image_url = None
                for idx, (mapped_scene, mapped_frame) in enumerate(frame_scene_map):
                    if (mapped_scene.scene_number == scene.scene_number and 
                        mapped_frame.frame_number == frame.frame_number):
                        image_url = image_urls[idx]
                        break
                
                # Create FrameWithImage object
                frame_with_image = FrameWithImage(
                    frame_number=frame.frame_number,
                    visual_prompt=frame.visual_prompt,
                    camera_angle=frame.camera_angle,
                    shot_type=frame.shot_type,
                    has_model=frame.has_model,
                    lighting=frame.lighting,
                    background_details=frame.background_details,
                    image_url=image_url
                )
                frames_with_images.append(frame_with_image)
            
            # Create SceneWithImages object
            scene_with_images = SceneWithImages(
                scene_number=scene.scene_number,
                scene_title=scene.scene_title,
                scene_purpose=scene.scene_purpose,
                setting=scene.setting,
                mood=scene.mood,
                frames=frames_with_images
            )
            scenes_with_images.append(scene_with_images)
        
        # Create VideoScriptWithImages object
        video_script_with_images = VideoScriptWithImages(
            product_category=video_script.product_category,
            product_name=video_script.product_name,
            video_title=video_script.video_title,
            video_hook=video_script.video_hook,
            target_audience=video_script.target_audience,
            video_objective=video_script.video_objective,
            scenes=scenes_with_images
        )
        
        return video_script_with_images
    except Exception as e:
        lg.error(f"Error building video script with images: {e}")
        return None

