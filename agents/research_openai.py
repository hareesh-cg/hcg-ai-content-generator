import os
import boto3
from openai import OpenAI # Or your chosen LLM client library

from utils.logger_config import get_logger

logger = get_logger(__name__)

# Initialize clients (can still be global in this module if desired)
s3_client = boto3.client('s3')
try:
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key or api_key == "NOT_SET":
         raise ValueError("OPENAI_API_KEY environment variable not set or invalid")
    llm_client = OpenAI(api_key=api_key)
except Exception as e:
    logger.error(f"Error initializing LLM client: {e}")
    llm_client = None

def generate_research_draft(post_id: str, blog_title: str, website_id: str, website_settings: dict, bucket_name: str) -> str:
    """
    Generates the research draft using OpenAI and saves it to S3.

    Args:
        post_id: The ID of the post.
        blog_title: The title of the blog post.
        website_id: The ID of the website (for S3 path).
        website_settings: Dictionary containing website context.
        bucket_name: The name of the S3 bucket to save the draft.

    Returns:
        The S3 URI of the saved raw article.

    Raises:
        ValueError: If inputs are missing or LLM fails.
        Exception: For S3 or other unexpected errors.
    """
    if not llm_client:
        logger.error("LLM Client not initialized during function call.")
        raise ValueError("LLM Client not initialized.")
    if not bucket_name:
         logger.error("S3 Bucket name environment variable not configured.")
         raise ValueError("S3 Bucket name environment variable not configured.")
    if not all([post_id, blog_title]):
        logger.error("Missing required input (postId, blogTitle, or websiteId).")
        raise ValueError("Missing required input: postId or blogTitle")

    logger.info(f"Generating research draft for Post ID: {post_id}, Title: {blog_title}")

    # Extract context from settings
    website_desc = website_settings.get('websiteDescription', '')
    target_audience = website_settings.get('targetAudience', '')
    core_keywords = website_settings.get('coreKeywords', [])

    # Construct Prompt (same as before)
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
            model="gpt-4o", # Or your chosen model
            messages=[
                {"role": "system", "content": "You are an expert researcher and technical writer."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
        )
        raw_article_content = response.choices[0].message.content
        if not raw_article_content:
            logger.error("LLM returned empty content for postId: %s", post_id)
            raise ValueError("LLM returned empty content.")

        logger.info("LLM response received. Content length:", len(raw_article_content))

        return raw_article_content

    except Exception as e:
        logger.exception(f"An error occurred during research draft generation for postId {post_id}")
        raise
    