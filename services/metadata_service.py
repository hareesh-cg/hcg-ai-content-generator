import os

from services.base_service import BaseContentService

from utils.logger_config import get_logger
from utils.errors import ServiceError
from utils import constants as Constants

from agents.metadata_openai import execute as generate_metadata_openai # Import agent's execute

logger = get_logger(__name__)

class MetadataService(BaseContentService): 
    """Orchestrates the SEO metadata generation process."""

    def __init__(self):
        super().__init__(service_name="MetadataService") 

    # --- Implement Abstract Properties ---
    @property
    def status_prefix(self) -> str:
        return "METADATA"

    @property
    def output_uri_db_key(self) -> str:
        # This service outputs a dictionary directly to DynamoDB
        return Constants.METADATA 

    # --- Implement Abstract Methods ---

    def _select_agent(self, website_settings: dict, post_item: dict | None = None, previous_step_output: any = None) -> callable:
        """Selects the metadata generation agent."""
        logger.info(f"[{self.service_name}] Selecting OpenAI agent for metadata.")
        return generate_metadata_openai # Return the agent's execute function

    def _call_agent(self, agent_function: callable, post_item: dict, website_settings: dict, previous_step_output: dict) -> any:
        """Downloads refined content and calls the metadata agent."""
        
        refined_article_uri = post_item.get(Constants.REFINED_ARTICLE_URI) 
        if not refined_article_uri:
             # ... (Error handling as in RefineService) ...
             raise ServiceError(...)
            
        # --- Download Refined Article ---
        logger.info(f"[{self.service_name}] Downloading refined article from {refined_article_uri}")
        refined_article_text = self.s3_helper.read_text_file(refined_article_uri)
        if refined_article_text is None: 
            raise ServiceError(...) # Error handling
        
        logger.info(f"[{self.service_name}] Refined article downloaded.")

        # Prepare event_data for the agent (it needs the content)
        event_data_for_agent = {"refined_article_content": refined_article_text}

        # Call the selected agent function
        # Agent returns a dictionary: {"metaTitle": ..., "metaDescription": ..., "keywords": [...]}
        metadata_dict = agent_function(
            post_item=post_item, # Pass post_item for title
            website_settings=website_settings, # Pass settings for instructions
            event_data=event_data_for_agent # Pass content here
        )
        
        # Return the metadata dictionary
        return metadata_dict


    def _save_agent_output(self, website_id: str, post_id: str, agent_output: any) -> str | None:
        """Saves the metadata dictionary directly to DynamoDB."""
        if not isinstance(agent_output, dict):
             logger.error(f"[{self.service_name}] Agent output was not a dictionary, cannot save metadata.")
             return None 

        logger.info(f"[{self.service_name}] Saving metadata to DynamoDB for postId {post_id}")
        
        # Use the generic update method from the DB helper
        # The key is the constant for the metadata attribute
        # The value is the dictionary itself (agent_output)
        update_success = self.db_helper.update_post_item(post_id, {Constants.METADATA: agent_output})

        if not update_success:
            logger.error(f"[{self.service_name}] Failed to save metadata to DynamoDB for postId {post_id}.")
            return None 
        
        logger.info(f"[{self.service_name}] Metadata successfully saved to DynamoDB for postId {post_id}.")
        # Return placeholder to signal success for this step
        return "DynamoDB_Updated"


    # --- Override Base Class DB Update Method ---
    def _update_db_uri(self, post_id: str, save_output_result: str | None):
        """Overrides the base method because metadata is saved directly in the item."""
        if save_output_result == "DynamoDB_Updated": 
             logger.info(f"[{self.service_name}] Metadata already saved to DynamoDB item for postId {post_id}. Skipping standard URI update.")
        else:
             logger.error(f"[{self.service_name}] _save_agent_output did not indicate successful DynamoDB update for postId {post_id}.")
        return save_output_result == "DynamoDB_Updated"