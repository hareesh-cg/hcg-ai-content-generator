# D:\Projects\Python\hcg-ai-content-generator\lambda_handlers\api_handler.py
import json
import os
from utils.logger_config import setup_logging, get_logger
from utils.errors import ServiceError

from services.research_service import ResearchService
from services.refine_service import RefineService
from services.image_prompt_service import ImagePromptService
from services.image_gen_service import ImageGenService
from services.metadata_service import MetadataService

setup_logging() 
logger = get_logger(__name__)

SERVICE_MAP = {
    "research": ResearchService,
    "refine": RefineService,
    "image_prompt": ImagePromptService,
    "image_gen": ImageGenService,
    "metadata": MetadataService,
}

# --- API Gateway Response Helper (remains the same) ---
def format_response(status_code, body_dict):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "GET,OPTIONS" # Only allowing GET for now
        },
        "body": json.dumps(body_dict)
    }

# --- Main Handler Function ---
def main(event, context):
    """
    API Gateway handler for various content generation functions, routed by query param.
    GET /content-api?functionName={func_name}&websiteId={websiteId}&postId={postId}
    """
    logger.debug("Received API Gateway event: %s", json.dumps(event, indent=2))
    
    function_name = None
    post_id = None 
    website_id = None

    try:
        # --- 1. Parse Query String Parameters ---
        query_params = event.get('queryStringParameters', {})
        if query_params is None: query_params = {}
             
        function_name = query_params.get('functionName')
        website_id = query_params.get('websiteId')
        post_id = query_params.get('postId')

        # Validate required parameters
        if not function_name:
            logger.warning("Missing 'functionName' query parameter.")
            return format_response(400, {"error": "Missing required query parameter: functionName"})
        if not website_id:
            logger.warning("Missing 'websiteId' query parameter.")
            return format_response(400, {"error": "Missing required query parameter: websiteId"})
        if not post_id:
            logger.warning("Missing 'postId' query parameter.")
            return format_response(400, {"error": "Missing required query parameter: postId"})

        logger.info(f"Handler invoked for functionName: '{function_name}', websiteId: '{website_id}', postId: '{post_id}'")

        # --- 2. Get appropriate Service Instance ---
        service_instance = get_service_instance(function_name)
        
        # --- 3. Prepare data and Call Service's Process Method ---
        # The base class process_request expects a dictionary
        event_data_for_service = {
            "postId": post_id,
            "websiteId": website_id
        }
        
        # The process_request method in the specific service (e.g., ResearchService)
        # will handle fetching necessary data (like websiteSettings, blogTitle)
        result = service_instance.process_request(event_data=event_data_for_service)

        # --- 4. Format Success Response ---
        logger.info(f"Request processed successfully for functionName '{function_name}', postId: {post_id}")
        return format_response(200, result) # Result dict comes from the service

    except ServiceError as se: 
        logger.error(f"Service Error processing request (functionName: {function_name}, postId: {post_id}): {se}") 
        return format_response(se.status_code, {"error": se.message}) 
    except Exception as e: 
        logger.exception(f"Unhandled error in handler (functionName: {function_name}, postId: {post_id})")
        return format_response(500, {"error": "An unexpected internal error occurred."})
    
def get_service_instance(function_name: str):
    """Gets an instance of the appropriate service class based on the function name."""

    logger.info(f"Attempting to get service instance for functionName: '{function_name}'")
    service_class = SERVICE_MAP.get(function_name.lower()) # Use lower case for case-insensitivity

    if not service_class:
        logger.error(f"Invalid function name provided: '{function_name}'")
        raise ServiceError(f"Invalid function name specified: {function_name}", 400, service_name="ServiceFactory")
    
    try:
        # Instantiate the selected service class
        service_instance = service_class() 
        return service_instance
    except ServiceError as se: # Catch init errors from Base class
        logger.exception(f"Initialization failed for service: {function_name}")
        # Re-raise the specific error from the service initializer
        raise se 
    except Exception as e:
        logger.exception(f"Unexpected error instantiating service: {function_name}")
        raise ServiceError(f"Could not initialize service for functionName '{function_name}'.", 500, service_name="ServiceFactory") from e