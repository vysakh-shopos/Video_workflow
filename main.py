import asyncio
from loguru import logger as lg
from app.models.image_generation import VideoScriptWithImages
from app.services.image_generation import generate_images
from app.services.video_generation import generate_videos
from app.services.script_writer import write_script
from app.services.analysis import analyze_product_image
from app.models.script_writer import VideoScript

lg.info("Starting the application")

async def main(image_url: str):
    try:
        lg.info("Application started successfully")
        # product_details = analyze_product_image(image_url)
        # video_script:VideoScript = write_script(product_category=product_details.get("product_category"), product_description=product_details.get("product_description"))
        import json
        # with open("video_scripts.json", "r") as f:
        #     video_script = json.load(f)
        # video_script:VideoScript = VideoScript(**video_script)
        # video_script_with_images = await generate_images(video_script, image_url)

        with open("video_scripts_images.json", "r") as f:
            video_script_with_images_json = json.load(f)
        video_script_with_images = VideoScriptWithImages(**video_script_with_images_json)
        
        # Generate videos from images
        lg.info("Starting video generation...")
        video_urls = await generate_videos(video_script_with_images)
        
        lg.info("Application completed successfully")
        return {
            "video_script": video_script_with_images,
            "video_urls": video_urls
        }
    except Exception as e:
        lg.error(f"Application failed to start: {e}")
        raise e

if __name__ == "__main__":
    asyncio.run(main("https://dev.cdn.pro.corp.shopos.ai/1763144221_760b4701beb3431ca65a38e3e2993c2d_original.png"))