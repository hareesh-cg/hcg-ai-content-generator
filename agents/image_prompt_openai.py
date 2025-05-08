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
    """Analyzes refined article text and generates image prompts using OpenAI."""

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
        raise
    
def generate_image_prompts_and_slugs(refined_article_content: str, website_settings: dict, num_prompts: int = 3) -> list[dict]:
    """Generates image prompts AND corresponding URL-safe slugs."""
    logger.info(f"Starting image prompt and slug generation. Aiming for {num_prompts}.")
    
    image_style = website_settings.get('imageStylePrompt', 'realistic photo')
    blog_title = website_settings.get('blogTitle', 'the article topic')

    # --- UPDATED PROMPT ---
    prompt = f"""
    Please act as a creative visual director and SEO assistant. Analyze the following article draft about "{blog_title}" and generate exactly {num_prompts} diverse and compelling text prompts suitable for an AI image generation model (like DALL-E 3). For EACH prompt, ALSO generate a short, descriptive, URL-safe slug (lowercase, alphanumeric, hyphens only) based on the prompt's core subject.

    **Instructions for Prompts:**
    - Each prompt should describe a distinct visual concept relevant to different sections or key ideas within the article.
    - Prompts should be descriptive, focusing on visual elements (subjects, actions, setting, mood, style).
    - Incorporate the desired overall image style: "{image_style}". Mention this style within each prompt.
    - Avoid prompts that are just summaries of text sections. Focus on visual representation.

    **Instructions for Slugs:**
    - Each slug should directly correspond to the image prompt it accompanies.
    - Slugs should be short (2-5 words typically).
    - Slugs must be URL-safe: use only lowercase letters, numbers, and hyphens (-). Replace spaces and other characters with hyphens. Remove articles like 'a', 'the'.
    - Slugs should capture the main subject or theme of the image prompt.

    **Output Format:**
    - Output **only** a valid JSON list of objects. Each object must have exactly two keys: "prompt" (string value) and "slug" (string value).
    - Example: [{{"prompt": "A futuristic cityscape with flying cars, {image_style}", "slug": "futuristic-cityscape-flying-cars"}}, {{"prompt": "...", "slug": "..."}}]

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

        # --- UPDATED PARSING ---
        try:
            output_data = json.loads(response_content)
            
            # Initialize empty list
            prompt_slug_list_raw = []

            # Check if the output is the expected list of dicts
            if isinstance(output_data, list):
                prompt_slug_list_raw = output_data
            # Check if it's a dictionary containing a list under a common key
            elif isinstance(output_data, dict):
                list_candidate = output_data.get("results") or output_data.get("prompts") or output_data.get("prompt_slug_list")
                if isinstance(list_candidate, list):
                    prompt_slug_list_raw = list_candidate
                # --- ADDED: Handle case where it returns a single dict ---
                elif "prompt" in output_data and "slug" in output_data:
                    logger.warning("LLM returned a single prompt/slug object instead of a list. Processing as a single item.")
                    prompt_slug_list_raw = [output_data] # Wrap the single dict in a list
                else:
                    logger.error(f"LLM returned a JSON dictionary but not in a recognized list format: {output_data}")
                    raise ValueError("LLM response was a dictionary but didn't contain the expected prompt/slug data structure.")
            else:
                logger.error(f"LLM response was valid JSON but neither a list nor a recognized dictionary format: {type(output_data)}")
                raise ValueError("LLM response was not a list or expected dictionary format.")

            # Now validate the contents of prompt_slug_list_raw
            validated_list = []
            if isinstance(prompt_slug_list_raw, list):
                for item in prompt_slug_list_raw:
                    # Validate each item is a dict with required keys
                    if isinstance(item, dict) and "prompt" in item and "slug" in item:
                        # Simple cleanup/validation for slug
                        slug = item.get("slug", f"image-{len(validated_list)}").lower()
                        slug = ''.join(c for c in slug if c.isalnum() or c == '-') 
                        slug = '-'.join(slug.split('-')) 
                        item["slug"] = slug if slug else f"image-{len(validated_list)}"
                        validated_list.append(item)
                    else:
                        logger.warning(f"Skipping invalid item in LLM response list: {item}")
            
            # Ensure we don't exceed requested number, even if LLM gave more
            final_prompts_slugs = validated_list[:num_prompts] 

            if not final_prompts_slugs:
                logger.error(f"LLM response parsed, but no valid prompt/slug pairs were found. Raw list was: {prompt_slug_list_raw}")
                raise ValueError("LLM response parsed, but yielded no valid prompt/slug pairs.")

            logger.info(f"Successfully parsed {len(final_prompts_slugs)} prompt/slug pairs from LLM response.")
            return final_prompts_slugs

        except (json.JSONDecodeError, TypeError, AttributeError) as json_e:
            logger.error(f"Failed to parse JSON response from LLM: {json_e}. Response was: {response_content}")
            raise ValueError("Failed to parse image prompt/slug list from LLM response.") from json_e

    except Exception as e:
        logger.exception("An error occurred during the image prompt/slug LLM call.")
        raise
    