import os
from openai import OpenAI
from utils.logger_config import get_logger

logger = get_logger(__name__)

# --- Initialize LLM Client ONLY ---
try:
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key or api_key == "NOT_SET":
         raise ValueError("OPENAI_API_KEY environment variable not set or invalid")
    # Use the same client initialized elsewhere if possible, but safe to re-init
    llm_client = OpenAI(api_key=api_key) 
    logger.info("OpenAI client initialized for ImageGenAgent.")
except Exception as e:
    logger.exception("CRITICAL: Error initializing LLM client for ImageGenAgent.")
    llm_client = None

def execute(post_item: dict, website_settings: dict, event_data: dict) -> str | None:
    """Generates an image using OpenAI's DALL-E model based on a prompt and settings."""
    prompt = event_data.get('prompt') # Get text from event_data
    if not prompt:
        logger.error("Missing 'prompt' in event_data for image gen agent.")
        raise ValueError("Missing 'prompt' for image gen agent.")

    logger.info(f"Starting image generation for prompt: '{prompt[:100]}...'") # Log snippet

    # Extract potential settings (aspect ratio might be useful)
    aspect_ratio = website_settings.get('imageAspectRatio', '16:9') # Example, DALL-E 3 might use '1024x1024', '1792x1024', '1024x1792'
    # Map aspect ratio to DALL-E 3 sizes if needed, or use default
    size = "1024x1024" # Default or choose based on aspect_ratio mapping
    if aspect_ratio == "16:9":
        size = "1792x1024"
    elif aspect_ratio == "9:16": # Example vertical
         size = "1024x1792"

    # Note: DALL-E 3 often performs better if style details are in the prompt itself,
    # rather than separate parameters, but 'style' parameter exists ('vivid' or 'natural').
    style_pref = website_settings.get('dalleStylePreference', 'vivid') # Example

    try:
        # --- Call DALL-E 3 API ---
        response = llm_client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size=size,
            quality="standard", # or "hd"
            style=style_pref, # vivid or natural
            n=1, # Generate one image per prompt
            # response_format='url' # Default is URL for DALL-E 3 via OpenAI lib
        )

        # --- Extract Image URL ---
        if response.data and len(response.data) > 0 and response.data[0].url:
            image_url = response.data[0].url
            logger.info(f"Image generated successfully. URL: {image_url}")
            # NOTE: This URL might be temporary depending on OpenAI's policies.
            # For long-term storage, downloading the image and saving to S3 is safer.
            # We will handle the download/re-upload in the S3 Helper for robustness.
            return image_url 
        else:
            logger.error(f"DALL-E API response did not contain expected image data/URL. Response: {response}")
            raise ValueError("Failed to retrieve image URL from DALL-E response.")

    except Exception as e:
        logger.exception(f"An error occurred during the DALL-E API call for prompt: '{prompt[:50]}...'")
        raise