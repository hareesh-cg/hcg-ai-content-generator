import json
import os
from agents.rewrite_openai import rewrite_article # Import the specific agent

from utils.logger_config import setup_logging, get_logger
setup_logging() # Configure root logger based on ENV var

logger = get_logger(__name__)

logger.info("Rewrite Handler Lambda Initialized")

# Get bucket name from environment variable once
bucket_name = os.environ.get('CONTENT_BUCKET_NAME')

def main(event, context):
    """
    AWS Lambda handler for the article rewrite step.
    Calls the rewrite agent.
    """
    logger.info(f"Received event: {json.dumps(event, indent=2)}")

    if not bucket_name:
         logger.error("Error: CONTENT_BUCKET_NAME environment variable not set.")
         raise ValueError("CONTENT_BUCKET_NAME not configured")

    try:
        # Extract data needed by the agent function
        # IMPORTANT: Expecting 'rawArticleUri' from the previous step's output
        post_id = event.get('postId')
        raw_article_uri = event.get('rawArticleUri') # Input from Research step
        website_settings = event.get('websiteSettings', {})
        blog_title = event.get('blogTitle') # Keep passing this along

        if not raw_article_uri:
            raise ValueError("Missing 'rawArticleUri' in input event.")

        # Call the agent function
        refined_s3_uri = rewrite_article(
            post_id=post_id,
            raw_article_uri=raw_article_uri,
            website_settings=website_settings,
            bucket_name=bucket_name
        )

        # Prepare output for the next Step Functions state
        output = {
            'postId': post_id,
            'blogTitle': blog_title,
            'websiteSettings': website_settings,
            'rawArticleUri': raw_article_uri, # Can optionally pass this along
            'refinedArticleUri': refined_s3_uri # Output for next step
        }

        # Return the dictionary directly for Step Functions state
        return output

    except Exception as e:
        logger.error(f"Error processing rewrite event for Post ID {post_id}: {e}")
        # Raise the exception to signal failure to Step Functions
        raise e