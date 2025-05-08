import os
import json
from openai import OpenAI

from utils.logger_config import get_logger
import re # For basic cleanup

logger = get_logger(__name__)

# (LLM Client Initialization as before) ...
try:
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key or api_key == "NOT_SET":
        raise ValueError("OPENAI_API_KEY environment variable not set or invalid")
    llm_client = OpenAI(api_key=api_key) 
    logger.info("OpenAI client initialized for SlugGenAgent.")
except Exception as e:
    logger.exception("CRITICAL: Error initializing LLM client for SlugGenAgent.")
    llm_client = None

def generate_slugs_from_prompts(image_prompts: list[str]) -> list[str]:
    """Generates URL-safe slugs based on a list of image prompts using OpenAI."""

    if not image_prompts:
        raise ValueError("No image prompts provided for slug generation.")

    logger.info(f"Starting slug generation for {len(image_prompts)} prompts.")
    
    # Prepare prompts for the LLM call. Send them as a numbered list.
    prompt_list_str = "\n".join([f"{i+1}. {p}" for i, p in enumerate(image_prompts)])

    prompt = f"""
    Analyze the following list of {len(image_prompts)} image prompts. For EACH prompt, generate a short, descriptive, URL-safe slug (lowercase, alphanumeric, hyphens only) based on the prompt's core subject.

    **Instructions for Slugs:**
    - Each slug should directly correspond to the image prompt in the same position in the list.
    - Slugs should be short (2-5 words typically).
    - Slugs must be URL-safe: use only lowercase letters, numbers, and hyphens (-). Replace spaces and other special characters with hyphens. Remove common articles (a, an, the). Consolidate multiple hyphens.
    - Slugs should capture the main subject or theme of the image prompt.
    - Output **only** a valid JSON list of strings, where each string is one slug. The list must contain exactly {len(image_prompts)} slugs in the same order as the input prompts.
    - Example Input Prompts:
      1. A futuristic cityscape with flying cars, clean flat vector illustration...
      2. Detailed diagram of a neural network node...
    - Example JSON Output: ["futuristic-cityscape-flying-cars", "neural-network-node-diagram"]

    **Input Image Prompts:**
    {prompt_list_str}

    Provide the JSON list of slugs below:
    """

    logger.info("Constructed Slug Generation Prompt - sending to LLM...")

    try:
        response = llm_client.chat.completions.create(
            model="gpt-4o", # Or gpt-3.5-turbo might be sufficient and cheaper
            response_format={ "type": "json_object" }, 
            messages=[
                 {"role": "system", "content": f"You are a helpful assistant generating JSON lists of URL-safe slugs based on input image prompts. Output only a valid JSON list of {len(image_prompts)} strings."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2, # Low temperature for more deterministic slugs
        )
        response_content = response.choices[0].message.content
        logger.debug(f"Raw LLM response for slugs: {response_content}")

        # --- Parse Response ---
        try:
            output_data = json.loads(response_content)
            # Expecting list directly or under key like "slugs"
            slug_list = output_data if isinstance(output_data, list) else output_data.get("slugs") or output_data.get("slug_list")
            
            if isinstance(slug_list, list) and all(isinstance(s, str) for s in slug_list):
                # Validate length
                if len(slug_list) != len(image_prompts):
                    logger.warning(f"LLM returned {len(slug_list)} slugs, expected {len(image_prompts)}. Will try to use matching slugs or generate defaults.")
                    # Pad with default slugs if too short, or truncate if too long
                    slug_list.extend([f"image-{i}" for i in range(len(slug_list), len(image_prompts))])
                    slug_list = slug_list[:len(image_prompts)]

                # Basic cleanup of returned slugs
                cleaned_slugs = []
                for i, slug in enumerate(slug_list):
                     clean_slug = re.sub(r'[^a-z0-9-]+', '', slug.lower())
                     clean_slug = re.sub(r'-+', '-', clean_slug).strip('-')
                     cleaned_slugs.append(clean_slug if clean_slug else f"image-{i}")

                logger.info(f"Successfully parsed and cleaned {len(cleaned_slugs)} slugs.")
                return cleaned_slugs
            else:
                 logger.error(f"LLM response was valid JSON but not the expected list of strings format for slugs: {output_data}")
                 raise ValueError("LLM did not return the expected JSON list format for slugs.")
        except (json.JSONDecodeError, TypeError, AttributeError) as json_e:
             logger.error(f"Failed to parse JSON response from LLM for slugs: {json_e}. Response was: {response_content}")
             raise ValueError("Failed to parse slug list from LLM response.") from json_e

    except Exception as e:
        logger.exception("An error occurred during the slug generation LLM call.")
        raise