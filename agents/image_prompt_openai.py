# D:\Projects\Python\hcg-ai-content-generator\agents\image_prompt_openai.py
import os
import json
from openai import OpenAI

from utils.logger_config import get_logger
from utils import constants as Constants

logger = get_logger(__name__)

# --- Initialize LLM Client ONLY ---
try:
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key or api_key == "NOT_SET":
         raise ValueError("OPENAI_API_KEY environment variable not set or invalid")
    llm_client = OpenAI(api_key=api_key)
    logger.info("OpenAI client initialized for ImagePromptAgent.")
except Exception as e:
    logger.exception("CRITICAL: Error initializing LLM client for ImagePromptAgent.")
    llm_client = None

def execute(post_item: dict, website_settings: dict, event_data: dict) -> list[dict]:
    """Generates image prompts AND corresponding URL-safe slugs."""

    refined_article_content = event_data.get('refined_article_content') # Get text from event_data
    if not refined_article_content:
        logger.error("Missing 'refined_article_content' in event_data for image prompt agent.")
        raise ValueError("Missing 'refined_article_content' for image prompt agent.")

    num_prompts = int(website_settings.get(Constants.NUM_IMAGE_PROMPTS, 3)) # Example: get desired number from settings    
    image_style = website_settings.get(Constants.IMAGE_STYLE_PROMPT, 'realistic photo') # Use Constant
    blog_title = post_item.get(Constants.BLOG_TITLE, 'the article topic') # Get from post_item

    logger.info(f"Starting image prompt and slug generation. Aiming for {num_prompts}.")

    prompt = f"""
    Please act as a creative visual director and SEO assistant. Analyze the following article draft about "{blog_title}" and generate **exactly {num_prompts}** diverse and compelling text prompts suitable for an AI image generation model (like DALL-E 3).

    **Instructions for Prompts:**
    - Each prompt should describe a distinct visual concept relevant to different sections or key ideas within the article.
    - Prompts should be descriptive, focusing on visual elements (subjects, actions, setting, mood, style).
    - Incorporate the desired overall image style: "{image_style}". Mention this style within each prompt.
    - Avoid prompts that are just summaries of text sections. Focus on visual representation.
    

    **Output Format:**
    - Output **only** a valid JSON list of objects containing **exactly {num_prompts}** objects.
    - Example: ["A futuristic cityscape with flying cars, {image_style}", "A serene forest with a mystical creature, {image_style}", "A close-up of a flower with dew drops, {image_style}"]
    - Example format: ["prompt 1...", "prompt 2...", "prompt 3..."]
    - Ensure the list contains **{num_prompts}** items.
    - Ensure the JSON is valid and well-formed.

    **Refined Article Draft:**
    --- START OF DRAFT ---
    {refined_article_content[:8000]} 
    --- END OF DRAFT (Snippet)--- 
    """ 
    
    logger.info("Constructed Image Prompt/Slug Generation Prompt - sending to LLM...")
    
    try:
        response = llm_client.chat.completions.create(
            model="gpt-4o", 
            response_format={ "type": "json_object" }, 
            messages=[
                 {"role": "system", "content": f"You are a helpful assistant generating JSON lists of image prompts and corresponding URL-safe slugs based on article text. Desired style: '{image_style}'. Follow format instructions precisely."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
        )
        response_content = response.choices[0].message.content
        logger.debug(f"Raw LLM response for image prompts/slugs: {response_content}")

        try:
            output_data = json.loads(response_content)
            # Expecting a list directly, or under a common key
            prompt_list = output_data if isinstance(output_data, list) else output_data.get("prompts") or output_data.get("image_prompts")

            if isinstance(prompt_list, list) and all(isinstance(p, str) for p in prompt_list):
                final_prompts = prompt_list[:num_prompts] # Trim if needed
                if len(final_prompts) < num_prompts:
                     logger.warning(f"LLM returned only {len(final_prompts)} prompts, expected {num_prompts}.")
                if not final_prompts: raise ValueError("LLM response yielded no valid prompts.")

                logger.info(f"Successfully parsed {len(final_prompts)} image prompts from LLM response.")
                return final_prompts
            else:
                 logger.error(f"LLM response was valid JSON but not the expected list of strings format: {output_data}")
                 raise ValueError("LLM did not return the expected JSON list format for prompts.")
        except (json.JSONDecodeError, TypeError, AttributeError) as json_e:
             logger.error(f"Failed to parse JSON response from LLM: {json_e}. Response was: {response_content}")
             raise ValueError("Failed to parse image prompt list from LLM response.") from json_e

    except Exception as e:
        logger.exception("An error occurred during the image prompt/slug LLM call.")
        raise
    