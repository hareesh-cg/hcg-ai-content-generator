import os
from utils.logger_config import get_logger
from utils.dynamodb_helper import DynamoDBHelper
from utils.s3_helper import S3Helper
from utils.errors import ServiceError

from agents.research_openai import generate_research_draft as generate_openai_draft
# from agents.research_gemini import generate_research_draft as generate_gemini_draft # Example

logger = get_logger(__name__)
SERVICE_NAME = "ResearchService"

class ResearchService:
    """Orchestrates the research article generation process."""

    def __init__(self):
        """Initializes dependencies (helpers)."""
        logger.info("Initializing ResearchService...")
        try:
            self.db_helper = DynamoDBHelper()
            self.s3_helper = S3Helper()
            logger.info("ResearchService initialized successfully.")
        except ValueError as e:
            # If helpers fail to init (e.g., missing env vars), service cannot operate
            logger.exception("Failed to initialize helpers in ResearchService.")
            raise ServiceError("Service initialization failed.", 500, service_name=SERVICE_NAME) from e

    def _select_agent(self, website_settings: dict):
        """Selects the appropriate agent based on config (future enhancement)."""
        # TODO: Implement logic to choose agent based on website_settings or global config
        # For now, default to OpenAI
        logger.info("Selecting OpenAI agent for research.")
        return generate_openai_draft

    def process_research_request(self, website_id: str, post_id: str) -> dict:
        """
        Handles the end-to-end research process for a given post.
        """
        final_status = "RESEARCH_FAILED" # Default status if error occurs early
        try:
            logger.info(f"Starting research process for websiteId: {website_id}, postId: {post_id}")

            # --- 1. Update Status: STARTED ---
            logger.info("--- 1. Update Status: STARTED ---")
            if not self.db_helper.update_post_status(post_id, "RESEARCH_STARTED"):
                 logger.warning(f"Failed to update status to STARTED for postId {post_id}. Continuing...")
                 # Decide if this is critical enough to stop

            # --- 2. Fetch Post & Validate Website ID ---
            logger.info("--- 2. Fetch Post & Validate Website ID ---")
            post_item = self.db_helper.get_post(post_id)
            if not post_item:
                raise ServiceError(f"Post with postId '{post_id}' not found.", 404, service_name=SERVICE_NAME)

            website_id_from_db = post_item.get('websiteId')
            blog_title = post_item.get('blogTitle')

            if not website_id_from_db:
                raise ServiceError(f"Post item '{post_id}' is missing websiteId attribute.", 500, service_name=SERVICE_NAME)
            if not blog_title:
                raise ServiceError(f"Post item '{post_id}' is missing blogTitle attribute.", 500, service_name=SERVICE_NAME)
            # Validate against the ID from the request (which came from query param)
            if website_id != website_id_from_db:
                logger.error(f"Forbidden: Query websiteId '{website_id}' != DB websiteId '{website_id_from_db}' for postId '{post_id}'")
                raise ServiceError("Access denied: Website ID mismatch.", 403, service_name=SERVICE_NAME)

            logger.info(f"Post data fetched and validated for postId: {post_id}")

            # --- 3. Fetch Website Settings ---
            logger.info("--- 3. Fetch Website Settings ---")
            website_settings = self.db_helper.get_website_settings(website_id)
            if not website_settings:
                raise ServiceError(f"Website settings for websiteId '{website_id}' not found.", 404, service_name=SERVICE_NAME)
            logger.info(f"Website settings fetched for websiteId: {website_id}")

            # --- 4. Select and Call Agent ---
            logger.info("--- 4. Select and Call Agent ---")
            research_agent_func = self._select_agent(website_settings)
            logger.info(f"Calling agent function {research_agent_func.__name__}...")
            raw_article_text = research_agent_func( # Agent only needs content generation context
                blog_title=blog_title,
                website_settings=website_settings
            )
            if not raw_article_text: # Agent should raise error, but double-check
                 raise ServiceError("Agent returned empty content.", 500, service_name=SERVICE_NAME)
            logger.info(f"Agent returned content. Length: {len(raw_article_text)}")

            # --- 5. Save Output to S3 ---
            logger.info("--- 5. Save Output to S3 ---")
            s3_key = f"{website_id}/{post_id}/research_article.txt"
            logger.info(f"Saving research article text to S3 - {s3_key}")
            s3_uri = self.s3_helper.save_text_file(key=s3_key, content=raw_article_text)

            if not s3_uri:
                raise ServiceError("Failed to save generated article to S3.", 500, service_name=SERVICE_NAME)
            logger.info(f"Article saved successfully to: {s3_uri}")

            # --- 6. Update Post Item URI ---
            logger.info("--- 6. Update Post Item URI ---")
            logger.info(f"Updating post item '{post_id}' with researchArticleUri...")
            uri_update_success = self.db_helper.update_post_research_uri(post_id, s3_uri)
            if not uri_update_success:
                # Log warning but don't fail the whole request at this stage
                logger.warning(f"S3 save succeeded but failed to update research URI for {post_id}.")


            # --- 7. Update Status: COMPLETE ---
            logger.info("--- 7. Update Status: COMPLETE ---")
            final_status = "RESEARCH_COMPLETE" # Set final status before updating
            status_update_success = self.db_helper.update_post_status(post_id, final_status)
            if not status_update_success:
                 logger.warning(f"Article processed, but failed to update final status for {post_id}.")
                 # Still return success, but maybe indicate partial success in message?

            # --- 8. Prepare Success Result ---
            logger.info("--- 8. Prepare Success Result ---")
            logger.info(f"Successfully processed request for postId: {post_id}")
            return {
                "message": "Research article generated, saved, and post updated successfully." if status_update_success and uri_update_success else "Research article generated and saved; post update may have failed.",
                "postId": post_id,
                "researchArticleUri": s3_uri
            }

        except Exception as e:
            logger.exception(f"Error during research process for postId {post_id}")
            # Attempt to set failed status if possible
            if post_id: # Check if we have post_id
                logger.info(f"Attempting to update status to {final_status} for postId '{post_id}' due to error.")
                self.db_helper.update_post_status(post_id, final_status)
            # Re-raise original or custom error for handler
            if isinstance(e, ServiceError):
                raise # Re-raise specific service errors
            else:
                raise ServiceError("An unexpected error occurred during research processing.", 500, service_name=SERVICE_NAME) from e