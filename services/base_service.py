import os
from abc import ABC, abstractmethod # Import Abstract Base Classes tools

from utils.logger_config import get_logger
from utils.dynamodb_helper import DynamoDBHelper
from utils.s3_helper import S3Helper
from utils.errors import ServiceError
import utils.constants as Constants

logger = get_logger(__name__)

class BaseContentService(ABC):
    """
    Abstract Base Class for content generation services (Research, Rewrite, etc.).
    Handles the common workflow: fetch data, update status, call agent, save output, update db.
    """

    def __init__(self, service_name: str):
        """Initializes common dependencies."""
        self.service_name = service_name
        logger.info(f"Initializing {self.service_name}...")
        try:
            self.db_helper = DynamoDBHelper()
            self.s3_helper = S3Helper()
            # Agent client initialization happens within the specific agent modules
            logger.info(f"{self.service_name} initialized successfully.")
        except ValueError as e:
            logger.exception(f"Failed to initialize helpers in {self.service_name}.")
            # Propagate initialization errors
            raise ServiceError(f"{self.service_name} initialization failed.", 500, service_name=self.service_name) from e

    # --- Abstract Properties/Methods for Subclasses to Implement ---

    @property
    @abstractmethod
    def status_prefix(self) -> str:
        """Status string prefix when this service step starts, completes, fails."""
        pass

    @property
    @abstractmethod
    def output_uri_db_key(self) -> str:
        """The DynamoDB attribute name to store the output S3 URI for this step."""
        pass

    @abstractmethod
    def _select_agent(self, website_settings: dict, post_item: dict | None = None, previous_step_output: any = None) -> callable:
        """Selects and returns the specific agent function to call."""
        # Subclasses will implement logic to choose based on settings or defaults
        pass

    @abstractmethod
    def _call_agent(self, agent_function: callable, post_item: dict, website_settings: dict, previous_step_output: any = None) -> any:
        """Calls the selected agent function with appropriate arguments and returns its output."""
        # Subclasses will format inputs for their specific agent and call it
        pass

    @abstractmethod
    def _save_agent_output(self, website_id: str, post_id: str, agent_output: any) -> str | None:
        """Saves the agent's output (e.g., text, prompts) using the S3 helper and returns the S3 URI."""
        # Subclasses will define the S3 key structure and call s3_helper
        pass

    # --- Concrete Workflow Method ---

    def process_request(self, event_data: dict) -> dict:
        """Executes the common workflow for a content generation step."""

        post_id = event_data.get('postId')
        website_id = event_data.get('websiteId')

        if not post_id or not website_id:
             logger.error(f"{self.service_name}: Missing postId or websiteId in input data.")
             raise ServiceError("Missing required input data for service.", 400, service_name=self.service_name)

        current_status = f"{self.status_prefix}_FAILED" # Default status in case of early exit in error block
        
        try:
            logger.info(f"[{self.service_name}] Starting process for postId: {post_id}, websiteId: {website_id}")

            # --- 1. Update Status: STARTED ---
            logger.info("--- 1. Update Status: STARTED ---")

            self._update_status(post_id, f"{self.status_prefix}_STARTED")

            # --- 2. Fetch Post Data & Validate Website ID ---
            logger.info("--- 2. Fetch Post Data & Validate Website ID ---")

            post_item = self.db_helper.get_post(post_id)
            if not post_item:
                 raise ServiceError(f"Post with postId '{post_id}' not found.", 404, service_name=self.service_name)
            
            website_id_from_db = post_item.get(Constants.WEBSITE_ID)
            if not website_id_from_db:
                raise ServiceError(f"Post item '{post_id}' is missing websiteId attribute.", 500, service_name=self.service_name)
            
            # Validate against the ID from the request (which came from query param)
            if website_id != website_id_from_db:
                logger.error(f"Forbidden: Query websiteId '{website_id}' != DB websiteId '{website_id_from_db}' for postId '{post_id}'")
                raise ServiceError("Access denied: Website ID mismatch.", 403, service_name=self.service_name)
            
            # --- 3. Fetch Website Settings ---
            logger.info("--- 3. Fetch Website Settings ---")

            website_settings = self.db_helper.get_website_settings(website_id)
            if not website_settings:
                raise ServiceError(f"Website settings for websiteId '{website_id}' not found.", 404, service_name=self.service_name)
            logger.info(f"Website settings fetched for websiteId: {website_id}")
            
            # --- 4. Select Agent ---
            logger.info("--- 4. Select Agent ---")

            # Pass relevant data for agent selection if needed
            agent_function = self._select_agent(website_settings, post_item, event_data)

            # --- 5. Call Agent ---
            logger.info("--- 5. Call Agent ---")

            logger.info(f"[{self.service_name}] Calling agent function {agent_function.__name__}...")
            agent_output = self._call_agent(agent_function, post_item, website_settings, event_data)
            if agent_output is None: # Agent should raise errors, but check just in case
                raise ServiceError("Agent returned None or empty output.", 500, service_name=self.service_name)
            logger.info(f"[{self.service_name}] Agent completed.")

            # --- 6. Save Output to S3 ---
            logger.info("--- 6. Save Output to S3 ---")

            logger.info(f"[{self.service_name}] Saving agent output to S3...")
            s3_uri = self._save_agent_output(website_id, post_id, agent_output)
            if not s3_uri:
                raise ServiceError("Failed to save agent output to S3.", 500, service_name=self.service_name)
            logger.info(f"[{self.service_name}] Output saved successfully to: {s3_uri}")

            # --- 7. Update Post Item URI ---
            logger.info("--- 7. Update Post Item URI ---")

            self._update_db_uri(post_id, s3_uri)

            # --- 8. Update Status: COMPLETE ---
            logger.info("--- 8. Update Status: COMPLETE ---")

            current_status = f"{self.status_prefix}_COMPLETE" # Update before final status update
            self._update_status(post_id, current_status)

            # --- 9. Prepare Success Result ---
            logger.info("--- 9. Prepare Success Result ---")

            logger.info(f"[{self.service_name}] Successfully processed request for postId: {post_id}")
            # Return a dictionary containing the key output URI and potentially other data
            result = {
                "message": f"{self.service_name} processed successfully.",
                "postId": post_id,
                self.output_uri_db_key: s3_uri # Use the dynamic key name
            }
            return result

        except Exception as e:
            logger.exception(f"[{self.service_name}] Error during process for postId {post_id}")
            # Attempt final status update upon error
            self._update_status(post_id, current_status) # Tries to set FAILED (or STARTED if error was early)
            # Re-raise specific ServiceErrors, wrap others
            if isinstance(e, ServiceError):
                raise
            else:
                raise ServiceError(f"An unexpected error occurred during {self.service_name} processing.", 500, service_name=self.service_name) from e


    # --- Internal Helper Methods ---

    def _update_status(self, post_id: str, status: str):
        """Internal helper to update post status."""
        if not post_id: return # Cannot update if postId is missing
        logger.info(f"[{self.service_name}] Attempting to update status to '{status}' for postId '{post_id}'")
        # Use constant for attribute name
        success = self.db_helper.update_post_item(post_id, {Constants.POST_STATUS: status})
        if not success:
            logger.warning(f"[{self.service_name}] Failed to update status to '{status}' for postId {post_id}.")
        return success
    
    def _update_db_uri(self, post_id: str, s3_uri: str):
        """Internal helper to update the output URI in DynamoDB."""
        if not post_id or not s3_uri: return
        logger.info(f"[{self.service_name}] Updating DB record for postId '{post_id}' with key '{self.output_uri_db_key}'")
        # Use constant for attribute name from subclass property
        success = self.db_helper.update_post_item(post_id, {self.output_uri_db_key: s3_uri})
        if not success:
            logger.warning(f"[{self.service_name}] Failed to update URI using key '{self.output_uri_db_key}' for postId {post_id}.")
        return success