import os
from openai import OpenAI
from utils.logger_config import get_logger

logger = get_logger(__name__)

# --- Initialize LLM Client ONLY ---
try:
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key or api_key == "NOT_SET":
         raise ValueError("OPENAI_API_KEY environment variable not set or invalid")
    llm_client = OpenAI(api_key=api_key)
    logger.info("OpenAI client initialized for RewriteAgent.")
except Exception as e:
    logger.exception("CRITICAL: Error initializing LLM client for RewriteAgent.")
    llm_client = None

def rewrite_article_content(raw_article_content: str, website_settings: dict) -> str:
    """
    Rewrites the provided raw article text using OpenAI based on website settings.

    Args:
        raw_article_content: The full text of the raw article draft.
        website_settings: Dictionary containing website context, especially 
                          'brandTone', 'articleLengthMin', 'articleLengthMax', 'targetAudience'.

    Returns:
        The rewritten article text as a string.

    Raises:
        ValueError: If LLM client isn't initialized or LLM fails to return content.
        Exception: For other unexpected errors during LLM call.
    """
    if not llm_client:
        logger.error("LLM Client not initialized during rewrite function call.")
        raise ValueError("LLM Client not initialized.")
    if not raw_article_content:
        logger.warning("Received empty raw_article_content for rewrite.")
        return "" # Return empty if input is empty

    logger.info(f"Starting rewrite process. Original length: {len(raw_article_content)}")

    # --- Extract Settings and Construct Prompt ---
    brand_tone = website_settings.get('brandTone', 'neutral and informative')
    min_len_str = website_settings.get('articleLengthMin', '1500') # Keep as string for prompt
    max_len_str = website_settings.get('articleLengthMax', '2500') # Keep as string for prompt
    target_audience = website_settings.get('targetAudience', 'a general audience')
    blog_title = website_settings.get('blogTitle', 'the provided topic') # Get title if passed in settings

    # Construct detailed rewrite prompt
    prompt = f"""
    Please act as an expert copy editor and writer. Your task is to rewrite the following raw article draft on the topic "{blog_title}" to match specific brand guidelines and length constraints.

    **Brand Guidelines:**
    - Brand Tone: {brand_tone}
    - Target Audience: {target_audience}

    **Content Constraints:**
    - Retain all key factual information, concepts, and core arguments from the original draft. Do not omit important details or sections.
    - Ensure the final article flows logically and is highly engaging for the target audience.
    - Adjust the writing style, vocabulary, and sentence structure to perfectly match the specified brand tone.
    - The final article length MUST be between {min_len_str} and {max_len_str} words. Expand or condense sections, examples, or explanations thoughtfully as needed to meet this length requirement while preserving all key information.
    - Correct any grammatical errors, spelling mistakes, or awkward phrasing in the original draft.
    - Maintain or create appropriate headings and subheadings for structure and readability.
    - Output only the rewritten article content itself, including the title as the first line. Do not include any introductory or concluding remarks about the rewrite process itself.

    **Original Raw Article Draft:**
    --- START OF DRAFT ---
    {raw_article_content}
    --- END OF DRAFT ---

    Please provide the fully rewritten article below:
    """
    logger.info("Constructed Rewrite Prompt - sending to LLM...")
    # logger.debug(f"Rewrite prompt snippet: {prompt[:500]}...")

    try:
        # --- Call LLM API ---
        response = llm_client.chat.completions.create(
            model="gpt-4o", # Or other capable model like gpt-4-turbo
            messages=[
                {"role": "system", "content": f"You are an expert copy editor rewriting content to fit specific brand guidelines (Tone: {brand_tone}) and length constraints ({min_len_str}-{max_len_str} words). Preserve all key information."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.6, # Adjust temperature as needed for creativity vs. adherence
        )
        refined_article_content = response.choices[0].message.content
        if not refined_article_content:
             logger.error("LLM returned empty content after rewrite request.")
             raise ValueError("LLM returned empty content after rewrite request.")

        logger.info(f"LLM rewrite response received. Content length: {len(refined_article_content)}")
        # logger.debug(f"Rewrite response snippet: {refined_article_content[:200]}...")

        return refined_article_content

    except Exception as e:
        logger.exception("An error occurred during the article rewrite LLM call.")
        raise # Re-raise the exception to be caught by the service/handler