# D:\Projects\Python\hcg-ai-content-generator\services\rewrite_service.py
import os
from utils.logger_config import get_logger
from utils.dynamodb_helper import DynamoDBHelper
from utils.s3_helper import S3Helper
from agents.rewrite_openai import rewrite_article_content # Import the agent function
from utils.errors import ServiceError 

logger = get_logger(__name__)
SERVICE_NAME = "RewriteService"

class RewriteService:
    """Orchestrates the article rewrite process."""

    def __init__(self):
        """Initializes dependencies (helpers)."""
        logger.info(f"Initializing {SERVICE_NAME}...")
        try:
            self.db_helper = DynamoDBHelper()
            self.s3_helper = S3Helper()
            # Note: Agent initialization happens within the agent module itself
            logger.info(f"{SERVICE_NAME} initialized successfully.")
        except ValueError as e:
            logger.exception(f"Failed to initialize helpers in {SERVICE_NAME}.")
            raise ServiceError("Service initialization failed.", 500, service_name=SERVICE_NAME) from e

    def _select_agent(self, website_settings: dict):
        """Selects the appropriate rewrite agent (future enhancement)."""
        # TODO: Add logic if multiple rewrite agents exist
        logger.info("Selecting OpenAI agent for rewrite.")
        return rewrite_article_content

    def process_rewrite_request(self, website_id: str, post_id: str, research_article_uri: str, website_settings: dict) -> dict:
        """Handles the end-to-end rewrite process for a given post."""
        final_status = "REWRITE_FAILED"
        refined_s3_uri = None # Initialize in case of early failure

        try:
            logger.info(f"Starting rewrite process for websiteId: {website_id}, postId: {post_id}")
            if not research_article_uri:
                 raise ServiceError("Missing researchArticleUri input.", 400, service_name=SERVICE_NAME)

            # --- 1. Update Status: STARTED ---
            if not self.db_helper.update_post_status(post_id, "REWRITE_STARTED"):
                 logger.warning(f"Failed to update status to REWRITE_STARTED for postId {post_id}. Continuing...")

            # --- 2. Download Raw Article ---
            logger.info(f"Downloading raw article from {research_article_uri}")
            raw_article_text = self.s3_helper.read_text_file(research_article_uri)
            if raw_article_text is None: # Check if download failed
                raise ServiceError(f"Failed to download raw article from {research_article_uri}.", 500, service_name=SERVICE_NAME)
            
            # --- 3. Select and Call Rewrite Agent ---
            rewrite_agent_func = self._select_agent(website_settings)
            logger.info(f"Calling agent function {rewrite_agent_func.__name__}...")
            # Add blogTitle to settings dict if agent needs it (optional)
            # website_settings_for_agent = website_settings.copy()
            # post_item = self.db_helper.get_post(post_id) # Fetch if needed
            # if post_item: website_settings_for_agent['blogTitle'] = post_item.get('blogTitle')
            
            refined_article_text = rewrite_agent_func(
                raw_article_content=raw_article_text,
                website_settings=website_settings # Pass the whole settings dict
            )
            if not refined_article_text: 
                 raise ServiceError("Rewrite agent returned empty content.", 500, service_name=SERVICE_NAME)
            logger.info(f"Rewrite agent returned content. Length: {len(refined_article_text)}")

            # --- 4. Save Refined Article to S3 ---
            logger.info(f"Saving refined article text to S3...")
            # Construct the S3 key for the refined article
            refined_s3_key = f"{website_id}/{post_id}/refined_article.txt"
            # Use the generic save function
            refined_s3_uri = self.s3_helper.save_text_file(
                key=refined_s3_key,
                content=refined_article_text
            )
            if not refined_s3_uri:
                raise ServiceError("Failed to save refined article to S3.", 500, service_name=SERVICE_NAME)
            logger.info(f"Refined article saved successfully to: {refined_s3_uri}")

            # --- 5. Update Post Item (optional: add refinedArticleUri) ---
            # Decide if you want to store the refined URI in DynamoDB
            # update_success = self.db_helper.update_post_refined_uri(post_id, refined_s3_uri) # Example method call
            # if not update_success: logger.warning(...)

            # --- 6. Update Status: COMPLETE ---
            final_status = "REWRITE_COMPLETE"
            status_update_success = self.db_helper.update_post_status(post_id, final_status)
            if not status_update_success:
                 logger.warning(f"Article rewritten, but failed to update final status for {post_id}.")
                 # Still return success, but indicate partial failure in message?

            # --- 7. Prepare Success Result ---
            logger.info(f"Successfully processed rewrite request for postId: {post_id}")
            return {
                "message": "Article rewrite processed successfully." if status_update_success else "Article rewrite processed; post status update failed.",
                "postId": post_id,
                "refinedArticleUri": refined_s3_uri # Return the new URI
            }

        except Exception as e:
            logger.exception(f"Error during rewrite process for postId {post_id}")
            if post_id: self.db_helper.update_post_status(post_id, final_status)
            if isinstance(e, ServiceError):
                raise 
            else:
                raise ServiceError("An unexpected error occurred during rewrite processing.", 500, service_name=SERVICE_NAME) from e