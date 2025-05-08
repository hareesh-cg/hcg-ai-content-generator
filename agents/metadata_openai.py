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
    # Use the same client initialized elsewhere if possible, but safe to re-init
    llm_client = OpenAI(api_key=api_key) 
    logger.info("OpenAI client initialized for MetadataAgent.")
except Exception as e:
    logger.exception("CRITICAL: Error initializing LLM client for MetadataAgent.")
    llm_client = None

def execute(post_item: dict, website_settings: dict, event_data: dict) -> dict:
    """Generates SEO metadata (meta title, description, keywords) based on refined article text."""

    # --- Extract required info from inputs ---
    refined_article_content = event_data.get('refined_article_content')
    if not refined_article_content:
        raise ValueError("Missing 'refined_article_content' for metadata agent.")

    blog_title = post_item.get(Constants.BLOG_TITLE, "Article Title")
    seo_instructions = website_settings.get(Constants.SEO_INSTRUCTIONS, "Generate standard SEO metadata.")
    core_keywords_list = website_settings.get(Constants.CORE_KEYWORDS, [])

    logger.info(f"Starting metadata generation for title: {blog_title}")

    # --- Construct Prompt ---
    prompt = f"""
    Please act as an expert SEO analyst. Analyze the following refined article draft about "{blog_title}" and generate relevant SEO metadata.

    **Article Context:**
    - Focuses on the topic: "{blog_title}"
    - Core Website Keywords (if provided): {', '.join(core_keywords_list) if core_keywords_list else 'N/A'}
    - Specific SEO Instructions: {seo_instructions}

    **Instructions:**
    - Generate an SEO-optimized Meta Title (typically 50-60 characters). It should be compelling and include the primary keyword(s).
    - Generate a compelling Meta Description (typically 150-160 characters). It should accurately summarize the article and encourage clicks.
    - Generate a list of 5-10 relevant Keywords/Keyphrases (mix of short and long-tail) based *only* on the article's content. Include core website keywords only if they are also highly relevant to this specific article.
    - Consider the provided SEO instructions.
    - Output **only** a valid JSON object with the following exact keys: "metaTitle" (string), "metaDescription" (string), and "keywords" (list of strings).
    - Example JSON output: {{"metaTitle": "Example Title | Site Name", "metaDescription": "Short compelling summary...", "keywords": ["keyword1", "long tail keyword 2"]}}

    **Refined Article Draft:**
    --- START OF DRAFT ---
    {refined_article_content[:8000]} 
    --- END OF DRAFT (Snippet)--- 
    """ 
    
    logger.info(f"Constructed Metadata Generation Prompt - sending to LLM")

    try:
        # --- Call LLM API ---
        response = llm_client.chat.completions.create(
            model="gpt-4o", # Or gpt-3.5-turbo might suffice
            response_format={ "type": "json_object" }, 
            messages=[
                 {"role": "system", "content": "You are an SEO analyst generating metadata as a valid JSON object with keys 'metaTitle', 'metaDescription', and 'keywords'."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5, # Lower temperature for more predictable SEO text
        )
        
        response_content = response.choices[0].message.content
        logger.debug(f"Raw LLM response for metadata: {response_content}")

        # --- Parse Response ---
        try:
            metadata_dict = json.loads(response_content)
            # Basic validation of expected keys and types
            if not isinstance(metadata_dict, dict) or \
               "metaTitle" not in metadata_dict or \
               "metaDescription" not in metadata_dict or \
               "keywords" not in metadata_dict or \
               not isinstance(metadata_dict["keywords"], list):
                logger.error(f"LLM response JSON missing required keys or has wrong types: {metadata_dict}")
                raise ValueError("LLM did not return the expected JSON structure for metadata.")
                
            logger.info(f"Successfully parsed metadata from LLM response.")
            # Return the validated dictionary
            return metadata_dict 

        except (json.JSONDecodeError, TypeError, AttributeError) as json_e:
             logger.error(f"Failed to parse JSON response from LLM for metadata: {json_e}. Response was: {response_content}")
             raise ValueError("Failed to parse metadata JSON from LLM response.") from json_e

    except Exception as e:
        logger.exception(f"An error occurred during the metadata generation LLM call for title '{blog_title}'.")
        raise