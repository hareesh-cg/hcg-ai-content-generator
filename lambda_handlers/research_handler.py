import json
import os

from agents.research_openai import generate_research_draft # Import the agent

from services.research_service import ResearchService

from utils.logger_config import setup_logging, get_logger
from utils.errors import ServiceError

setup_logging() # Configure root logger based on ENV var
logger = get_logger(__name__)

logger.info("Research Handler Lambda Initialized (API Gateway Trigger)")

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
    GET /research?website={websiteId}&post={postId}
    """
    logger.debug(f"Received API Gateway event: {json.dumps(event, indent=2)}")
    
    post_id = None
    website_id = None

    try:
        # --- Parse Query Params ---
        query_params = event.get('queryStringParameters', {})
        if query_params is None: query_params = {}
        website_id = query_params.get('websiteId')
        post_id = query_params.get('postId')
        if not website_id or not post_id:
            logger.warning("Missing websiteId or postId in query string parameters.")
            return format_response(400, {"error": "Missing required query parameters: websiteId, postId"})

        logger.info(f"Handler invoked for websiteId: {website_id}, postId: {post_id}")

        # --- Instantiate and Call Service ---
        service = ResearchService()
        result = service.process_research_request(website_id=website_id, post_id=post_id)

        # --- Format Success Response ---
        logger.info(f"Request processed successfully for postId: {post_id}")
        return format_response(200, result)

    except ServiceError as se: # Catch specific service errors
        # Log includes service name and status code from the error object itself
        logger.error(f"Service Error processing request for postId '{post_id}': {se}") 
        return format_response(se.status_code, {"error": se.message}) # Use status code from error
    except Exception as e: # Catch unexpected errors (like service init failure)
        logger.exception(f"Unhandled error in handler for postId '{post_id}'")
        return format_response(500, {"error": "An unexpected internal error occurred."})
    