import os
import boto3
from openai import OpenAI # Or your chosen LLM client library

from utils.logger_config import get_logger
from utils import constants as Constants

logger = get_logger(__name__)

# Initialize clients (can still be global in this module if desired)
try:
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key or api_key == "NOT_SET":
         raise ValueError("OPENAI_API_KEY environment variable not set or invalid")
    llm_client = OpenAI(api_key=api_key)
    logger.info("OpenAI client initialized.")
except Exception as e:
    logger.exception("CRITICAL: Error initializing LLM client.")
    llm_client = None

def execute(post_item: dict, website_settings: dict, event_data: dict | None = None) -> str:
    """Generates the research draft text using OpenAI based on input context."""
    
    if not llm_client:
        logger.error("LLM Client not initialized during function call.")
        raise ValueError("LLM Client not initialized.")
    
    blog_title = post_item.get(Constants.BLOG_TITLE)
    if not blog_title:
         logger.error(f"Missing '{Constants.BLOG_TITLE}' in post_item for postId '{post_item.get(Constants.POST_ID)}'")
         raise ValueError(f"Missing '{Constants.BLOG_TITLE}' in post item.")
    
    logger.info(f"Generating research draft for Title: {blog_title}")

    # Extract context from settings
    website_desc = website_settings.get(Constants.WEBSITE_DESCRIPTION, '')
    target_audience = website_settings.get(Constants.TARGET_AUDIENCE, 'a general audience')
    core_keywords = website_settings.get(Constants.CORE_KEYWORDS, [])

    prompt = f"""
    Please act as an expert researcher and writer. Your task is to generate a comprehensive, deeply researched draft article on the topic: "{blog_title}".

    **Context about the target website:**
    - Description: {website_desc}
    - Target Audience: {target_audience}
    - Core Keywords: {', '.join(core_keywords) if core_keywords else 'N/A'}

    **Instructions:**
    - Conduct thorough research on the topic "{blog_title}". Cover all essential aspects, history (if relevant), current state, key concepts, examples, potential future developments, and related topics.
    - Structure the article logically with clear headings and subheadings.
    - The tone should be informative and authoritative, suitable for the target audience.
    - Aim for significant depth and detail. This is a first draft, so prioritize comprehensiveness over perfect prose or strict length limits at this stage.
    - Ensure factual accuracy.
    - Do **NOT** include placeholder text like "[Insert details here]". Generate the full content.
    - Output only the researched article content itself, starting with the title. Do not include introductory or concluding remarks about the generation process itself.
    """
    logger.info("Constructed Prompt - sending to LLM...")

    try:
        # Call LLM API
        response = llm_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert researcher and technical writer."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
        )
        raw_article_content = response.choices[0].message.content
        if not raw_article_content:
            logger.error(f"LLM returned empty content for title: {blog_title}")
            raise ValueError("LLM returned empty content.")

        logger.info(f"LLM response received. Content length: {len(raw_article_content)}")

        return raw_article_content

    except Exception as e:
        logger.exception(f"An error occurred during research draft generation for title '{blog_title}': {e}")
        raise
