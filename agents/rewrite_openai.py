import os
import boto3
from openai import OpenAI
import json # To potentially load settings if passed as JSON string

from utils.logger_config import get_logger

logger = get_logger(__name__)

# Initialize clients (can reuse if module loaded multiple times, but safe to repeat)
s3_client = boto3.client('s3')
try:
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key or api_key == "NOT_SET":
         raise ValueError("OPENAI_API_KEY environment variable not set or invalid")
    llm_client = OpenAI(api_key=api_key)
except Exception as e:
    logger.error(f"Error initializing LLM client: {e}")
    llm_client = None

def rewrite_article(post_id: str, raw_article_uri: str, website_settings: dict, bucket_name: str) -> str:
    """
    Downloads a raw article, rewrites it using OpenAI based on website settings,
    and saves the refined article to S3.

    Args:
        post_id: The ID of the post.
        raw_article_uri: The S3 URI of the raw article text file (e.g., "s3://bucket/path/file.txt").
        website_settings: Dictionary containing website context, especially brandTone, length constraints.
        bucket_name: The name of the S3 bucket.

    Returns:
        The S3 URI of the saved refined article.

    Raises:
        ValueError: If inputs are missing, LLM fails, or article download fails.
        Exception: For S3 or other unexpected errors.
    """
    if not llm_client:
        raise ValueError("LLM Client not initialized.")
    if not bucket_name:
         raise ValueError("S3 Bucket name environment variable not configured.")
    if not all([post_id, raw_article_uri]):
        raise ValueError("Missing required input: postId or rawArticleUri")

    logger.info(f"Rewriting article for Post ID: {post_id} from URI: {raw_article_uri}")

    # --- 1. Download Raw Article from S3 ---
    try:
        # Parse S3 URI
        if not raw_article_uri.startswith("s3://"):
            raise ValueError(f"Invalid S3 URI format: {raw_article_uri}")
        
        uri_parts = raw_article_uri[5:].split('/', 1)
        source_bucket = uri_parts[0]
        source_key = uri_parts[1]
        
        logger.info(f"Downloading from bucket '{source_bucket}', key '{source_key}'")
        s3_object = s3_client.get_object(Bucket=source_bucket, Key=source_key)
        raw_article_content = s3_object['Body'].read().decode('utf-8')
        logger.info(f"Downloaded raw article. Length: {len(raw_article_content)}")
        
    except Exception as e:
        logger.error(f"Error downloading raw article from S3: {e}")
        # Re-raise or handle appropriately
        raise ValueError(f"Failed to download raw article from {raw_article_uri}") from e

    # --- 2. Extract Settings and Construct Prompt ---
    brand_tone = website_settings.get('brandTone', 'neutral and informative')
    min_len = website_settings.get('articleLengthMin', 1500) # Default min
    max_len = website_settings.get('articleLengthMax', 2500) # Default max
    target_audience = website_settings.get('targetAudience', 'a general audience')

    # Construct detailed rewrite prompt
    prompt = f"""
    Please act as an expert copy editor and writer. Your task is to rewrite the following raw article draft to match specific brand guidelines and length constraints.

    **Brand Guidelines:**
    - Brand Tone: {brand_tone}
    - Target Audience: {target_audience}

    **Content Constraints:**
    - Retain all key factual information, concepts, and core arguments from the original draft. Do not omit important details.
    - Ensure the final article flows logically and is engaging for the target audience.
    - Adjust the writing style, vocabulary, and sentence structure to perfectly match the specified brand tone.
    - The final article length MUST be between {min_len} and {max_len} words. Adjust the level of detail, examples, or explanations as needed to meet this length requirement while preserving key information.
    - Correct any grammatical errors or awkward phrasing in the original draft.
    - Structure the output with clear headings and subheadings as appropriate.
    - Output only the rewritten article content itself. Do not include introductory or concluding remarks about the rewrite process.

    **Original Raw Article Draft:**
    --- START OF DRAFT ---
    {raw_article_content}
    --- END OF DRAFT ---

    Please provide the rewritten article below:
    """
    logger.debug("Constructed Rewrite Prompt - sending to LLM...")

    # --- 3. Call LLM API ---
    response = llm_client.chat.completions.create(
        model="gpt-4o", # Or another capable model
        messages=[
            {"role": "system", "content": f"You are an expert copy editor rewriting content to fit specific brand guidelines (Tone: {brand_tone}) and length constraints ({min_len}-{max_len} words)."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.6, # Slightly lower temperature might be better for refining
    )
    refined_article_content = response.choices[0].message.content
    if not refined_article_content:
         raise ValueError("LLM returned empty content after rewrite request.")

    logger.info(f"LLM rewrite response received. Content length: {len(refined_article_content)}")
    # You might want to add a word count check here before saving

    # --- 4. Save Refined Article to S3 ---
    # Define a new key for the refined article
    refined_s3_key = f"posts/{post_id}/refined_article.txt"
    logger.info(f"Uploading refined article to s3://{bucket_name}/{refined_s3_key}")
    s3_client.put_object(
        Bucket=bucket_name,
        Key=refined_s3_key,
        Body=refined_article_content.encode('utf-8'),
        ContentType='text/plain'
    )
    logger.info("Upload successful.")

    refined_s3_uri = f"s3://{bucket_name}/{refined_s3_key}"
    return refined_s3_uri