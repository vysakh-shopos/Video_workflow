import requests
from loguru import logger as lg

def get_url(image_url: str) -> bytes:
    """
    Download and return the content from a URL as bytes.
    
    Args:
        image_url: URL to download from
        
    Returns:
        bytes: Content of the URL or None if download fails
    """
    try:
        response = requests.get(image_url)
        return response.content
    except Exception as e:
        lg.error(f"Error getting URL: {e}")
        return None


def validate_url(image_url: str) -> str:
    """
    Validate that a URL is accessible and return the URL string.
    Useful for passing URLs to APIs that need URL strings, not bytes.
    
    Args:
        image_url: URL to validate
        
    Returns:
        str: The validated URL or None if validation fails
    """
    try:
        # Validate that the URL is accessible
        response = requests.head(image_url, timeout=5)
        response.raise_for_status()
        return image_url
    except Exception as e:
        lg.error(f"Error validating URL {image_url}: {e}")
        return None


if __name__ == "__main__":
    url = get_url("https://dev.cdn.pro.corp.shopos.ai/1763144221_760b4701beb3431ca65a38e3e2993c2d_original.png")
    print(url)