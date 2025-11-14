import asyncio, os, json
import time
from loguru import logger as lg
from app.models.image_generation import VideoScriptWithImages
from app.services.ai_video_editor import AIVideoEditor
from app.services.image_generation import generate_images
from app.services.video_generation import generate_videos
from app.services.script_writer import write_script
from app.services.analysis import analyze_product_image
from app.models.script_writer import VideoScript

lg.info("Starting the application")
BASE_DIR ="outputs/"

def save_to_json(data, output_path):
    try:
        with open(os.path.join(output_path), "w") as f:
            json.dump(data, f)
    except Exception as e:
        lg.error(f"Error saving to JSON: {e}")


async def main(image_url: str,output_name: str, user_text:str=""):
    try:
        lg.info(f"Starting application for {output_name}")
        start_time = time.time()
        output_path = os.path.join(BASE_DIR, output_name)
        os.makedirs(output_path, exist_ok=True)
        lg.info("Application started successfully")
        product_details = analyze_product_image(image_url)
        save_to_json(product_details, os.path.join(output_path, "product_details.json"))

        video_script:VideoScript = write_script(product_category=product_details.get("product_category"), product_description=product_details.get("product_description"), user_text=user_text)
        save_to_json(video_script.model_dump(), os.path.join(output_path, "video_script.json"))

        video_script_with_images = await generate_images(video_script, image_url)
        save_to_json(video_script_with_images.model_dump(), os.path.join(output_path, "video_script_with_images.json"))
        
        # Generate videos from images
        lg.info("Starting video generation...")
        video_urls = await generate_videos(video_script_with_images)
        save_to_json(video_urls, os.path.join(output_path, "video_urls.json"))
        ai_video_editor = AIVideoEditor()

        final_video_result = ai_video_editor.stitch_videos(video_urls, os.path.join(output_path, "final_video.mp4"))
        save_to_json(final_video_result, os.path.join(output_path, "final_video_result.json"))
        end_time = time.time()
        lg.info(f"Application completed in {end_time - start_time:.2f} seconds")

        lg.info("Application completed successfully")
        return {
            "video_script": video_script_with_images,
            "video_urls": video_urls,
            "final_video": final_video_result
        }
    except Exception as e:
        lg.error(f"Application failed to start: {e}")
        raise e

if __name__ == "__main__":
    # asyncio.run(main("https://dev.cdn.pro.corp.shopos.ai/1763144221_760b4701beb3431ca65a38e3e2993c2d_original.png","tshirt_video_custom"))
    asyncio.run(main("https://dev.cdn.pro.corp.shopos.ai/1759991733-generated_image_a0ee3e4f-99f8-463c-a6b1-8b132caa41b0_1.jpeg","shoes", " create a lifestyle video for this shoes"))

    