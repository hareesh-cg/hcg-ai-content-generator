# D:\Projects\Python\hcg-ai-content-generator\lambda_handlers\research_handler.py
import json
import os

from utils.dynamodb_helper import DynamoDBHelper # Import the new helper
from utils.s3_helper import S3Helper

from agents.research_openai import generate_research_draft # Import the agent

from utils.logger_config import setup_logging, get_logger

setup_logging() # Configure root logger based on ENV var
logger = get_logger(__name__)

logger.info("Research Handler Lambda Initialized (API Gateway Trigger)")

# Initialize helper outside handler (can raise error on cold start if config missing)
try:
    db_helper = DynamoDBHelper()
    s3_helper = S3Helper()
except ValueError as e:
    logger.critical(f"CRITICAL INIT ERROR: {e}")
    db_helper = None
    s3_helper = None
    # Ensure handler fails cleanly if init fails

# Get bucket name from environment variable once
bucket_name = os.environ.get('CONTENT_BUCKET_NAME')

logger.info("Handler Initialized.")

# --- Helper Function for API Gateway Response ---
def format_response(status_code, body_dict):
    return {
        "statusCode": status_code,
        "headers": {
            # Add CORS headers if your API will be called from a web browser
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*", # Be more specific in production
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "GET,OPTIONS" 
        },
        "body": json.dumps(body_dict)
    }

def main(event, context):
    """
    API Gateway handler for triggering the research process.
    GET /research/website/{websiteId}/post/{postId}
    """
    logger.info(f"Received API Gateway event: {json.dumps(event, indent=2)}")

    # Check if initialization failed
    if not db_helper:
        return format_response(500, {"error": "Internal server configuration error (DB Helper)."})
    if not bucket_name:
        logger.error("Error: CONTENT_BUCKET_NAME environment variable not set.")
        return format_response(500, {"error": "Internal server configuration error (Bucket Name)."})
    
    post_id_from_path = None 
    website_id_from_path = None

    try:
        # --- 1. Parse Path Parameters ---
        path_params = event.get('pathParameters', {})
        website_id_from_path = path_params.get('websiteId')
        post_id_from_path = path_params.get('postId')

        if not website_id_from_path or not post_id_from_path:
            logger.error("Missing path parameters in request.")
            return format_response(400, {"error": "Missing websiteId or postId in path parameters."})

        logger.info(f"Extracted websiteId: {website_id_from_path}, postId: {post_id_from_path}")

        # --- 2. Fetch Post & Validate Website ID using Helper ---
        post_item = db_helper.get_post(post_id_from_path)
        if not post_item:
            logger.error(f"Post item with postId '{post_id_from_path}' not found.")
            return format_response(404, {"error": f"Post with postId '{post_id_from_path}' not found."})

        website_id_from_db = post_item.get('websiteId')
        blog_title = post_item.get('blogTitle')

        if not website_id_from_db:
            logger.error(f"Post item '{post_id_from_path}' is missing websiteId attribute.")
            return format_response(500, {"error": f"Post item '{post_id_from_path}' is missing websiteId attribute."})
        if not blog_title:
            logger.error(f"Post item '{post_id_from_path}' is missing blogTitle attribute.")
            return format_response(500, {"error": f"Post item '{post_id_from_path}' is missing blogTitle attribute."})
        if website_id_from_path != website_id_from_db:
            logger.error(f"Forbidden: Path websiteId '{website_id_from_path}' does not match item's websiteId '{website_id_from_db}'")
            return format_response(403, {"error": "Access denied: Website ID mismatch."})

        website_id = website_id_from_db # Use validated ID
        logger.info(f"WebsiteId validated: {website_id}")

        # --- 3. Fetch Website Settings using Helper ---
        website_settings = db_helper.get_website_settings(website_id)
        if not website_settings:
            logger.error(f"Website settings for websiteId '{website_id}' not found.")
            return format_response(404, {"error": f"Website settings for websiteId '{website_id}' not found."})

        # --- 4. Call the Research Agent ---
        logger.info(f"Calling research agent for postId '{post_id_from_path}'...")
        raw_article_text = generate_research_draft(
            blog_title=blog_title,
            website_settings=website_settings
        )
        logger.info(f"Agent completed. Received text length: {len(raw_article_text)}")

        # --- 5. Save Agent Output using S3 Helper ---
        logger.info(f"Saving research article text to S3 for postId '{post_id_from_path}'...")
        s3_key = f"{website_id}/{post_id_from_path}/research_article.txt"
        s3_uri = s3_helper.save_text_file(
            key=s3_key,
            content=raw_article_text
        )
        if not s3_uri:
            logger.error(f"Failed to save research article to S3 for postId '{post_id_from_path}'.")
            # Decide how to handle - maybe still update DB with error? Or fail request?
            return format_response(500, {"error": "Failed to save generated article."})
        
        logger.info(f"Article saved successfully to: {s3_uri}")

        # --- 6. Update Post Item using Helper ---
        logger.info(f"Updating post item '{post_id_from_path}' with researchArticleUri...")
        update_success = db_helper.update_post_research_uri(post_id_from_path, s3_uri)

        if not update_success:
            # Log the error but return success as the main task completed
            logger.warning(f"Warning: Article generated but failed to update post status for {post_id_from_path}.")
            return format_response(200, {
                "message": "Research article generated but failed to update post status in DynamoDB.",
                "postId": post_id_from_path,
                "researchArticleUri": s3_uri
            })

        # --- 7. Return Success Response ---
        logger.info(f"Post item '{post_id_from_path}' updated successfully with researchArticleUri: {s3_uri}.")
        return format_response(200, {
            "message": "Research article generated and post updated successfully.",
            "postId": post_id_from_path,
            "researchArticleUri": s3_uri
        })

    except ValueError as ve: # Catch specific validation/config errors
        logger.error(f"Value Error: {ve}")
        return format_response(400, {"error": str(ve)})
    except Exception as e: # Catch unexpected errors
        logger.error(f"Unhandled error processing request: {e}")
        return format_response(500, {"error": "An unexpected error occurred."})
    