# D:\Projects\Python\hcg-ai-content-generator\agents\image_prompt_openai.py
import os
import json
from openai import OpenAI
from utils.logger_config import get_logger

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

def generate_image_prompts(refined_article_content: str, website_settings: dict, num_prompts: int = 3) -> list[str]:
    """
    Analyzes refined article text and generates image prompts using OpenAI.

    Args:
        refined_article_content: The full text of the refined article.
        website_settings: Dictionary containing website context, especially 'imageStylePrompt'.
        num_prompts: The desired number of prompts to generate.

    Returns:
        A list of generated image prompt strings.

    Raises:
        ValueError: If LLM client isn't initialized or LLM fails.
        Exception: For other unexpected errors.
    """
    if not llm_client:
        logger.error("LLM Client not initialized during image prompt function call.")
        raise ValueError("LLM Client not initialized.")
    if not refined_article_content:
        logger.warning("Received empty refined_article_content for image prompt generation.")
        return []

    logger.info(f"Starting image prompt generation. Aiming for {num_prompts} prompts.")

    # --- Extract Settings and Construct Prompt ---
    image_style = website_settings.get('imageStylePrompt', 'realistic photo') # Default style
    blog_title = website_settings.get('blogTitle', 'the article topic') # Get title if available

    # Construct prompt asking for JSON output for easier parsing
    prompt = f"""
    Please act as a creative visual director. Analyze the following article draft about "{blog_title}" and generate exactly {num_prompts} diverse and compelling text prompts suitable for an AI image generation model (like DALL-E 3 or Midjourney).

    **Instructions:**
    - Each prompt should describe a distinct visual concept relevant to different sections or key ideas within the article.
    - Prompts should be descriptive, focusing on visual elements (subjects, actions, setting, mood, style).
    - Incorporate the desired overall image style: "{image_style}". Mention this style within each prompt.
    - Avoid prompts that are just summaries of text sections. Focus on visual representation.
    - Make the prompts creative and engaging.
    - Output **only** a valid JSON list of strings, where each string is one image prompt. Example format: ["prompt 1...", "prompt 2...", "prompt 3..."]

    **Refined Article Draft:**
    --- START OF DRAFT ---
    {refined_article_content[:8000]} 
    --- END OF DRAFT (Snippet)--- 
    """ 
    # Note: Truncated input to manage token limits if article is very long. Adjust as needed.

    logger.info("Constructed Image Prompt Generation Prompt - sending to LLM...")
    # logger.debug(f"Image prompt generation request snippet: {prompt[:500]}...")

    try:
        # --- Call LLM API ---
        # Request JSON output (supported by newer OpenAI models)
        response = llm_client.chat.completions.create(
            model="gpt-4o", # Or gpt-4-turbo which is good at JSON
            response_format={ "type": "json_object" }, # Request JSON
            messages=[
                {"role": "system", "content": f"You are a helpful assistant that generates image prompts based on article text, following instructions precisely and outputting only a valid JSON list of strings. The desired style is '{image_style}'."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8, # Higher temperature for more creative prompts
        )
        
        response_content = response.choices[0].message.content
        logger.debug(f"Raw LLM response for image prompts: {response_content}")

        # --- Parse Response ---
        try:
            # Assuming the response content is a JSON string like '{"prompts": ["p1", "p2"]}'
            # Adjust parsing based on actual LLM output structure if needed.
            # Often models output a dict with a key, e.g. "image_prompts" or "prompts"
            output_data = json.loads(response_content)
            # Try common keys for the list of prompts
            prompt_list = output_data.get("prompts") or output_data.get("image_prompts") or output_data.get("imagePrompts")
            
            if isinstance(prompt_list, list) and all(isinstance(p, str) for p in prompt_list):
                 # Ensure we got roughly the right number, trim if needed
                final_prompts = prompt_list[:num_prompts] 
                logger.info(f"Successfully parsed {len(final_prompts)} image prompts from LLM response.")
                return final_prompts
            else:
                 logger.error(f"LLM response was valid JSON but not the expected list of strings format: {output_data}")
                 raise ValueError("LLM did not return the expected JSON list format for prompts.")
        except (json.JSONDecodeError, TypeError, AttributeError) as json_e:
             logger.error(f"Failed to parse JSON response from LLM: {json_e}. Response was: {response_content}")
             # Attempt fallback if it just returned a simple list string? Less reliable.
             raise ValueError("Failed to parse image prompt list from LLM response.") from json_e

    except Exception as e:
        logger.exception("An error occurred during the image prompt LLM call.")
        raise # Re-raise the exception