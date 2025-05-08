import os

from utils.logger_config import get_logger
from services.base_service import BaseContentService # Import base class
from utils.dynamodb_helper import DynamoDBHelper # For constants
from utils.s3_helper import S3Helper # Needed to read input
from utils.errors import ServiceError
import utils.constants as Constants

# Import the specific agent implementation
from agents.refine_openai import execute as refine_openai_content

logger = get_logger(__name__)

class RefineService(BaseContentService): # Inherit from base
    """Orchestrates the article refine process."""

    def __init__(self):
        # Initialize the base class
        super().__init__(service_name="RefineService") 

    # --- Implement Abstract Properties ---
    @property
    def status_prefix(self) -> str:
        return "REFINE"

    @property
    def output_uri_db_key(self) -> str:
        # The DynamoDB attribute name for this service's output URI
        return Constants.REFINED_ARTICLE_URI # Use constant from helper

    # --- Implement Abstract Methods ---

    def _select_agent(self, website_settings: dict, post_item: dict | None = None, previous_step_output: any = None) -> callable:
        """Selects the refine agent."""
        # TODO: Add logic if multiple refine agents exist
        logger.info(f"[{self.service_name}] Selecting OpenAI agent for refine.")
        return refine_openai_content # Return the function object

    def _call_agent(self, agent_function: callable, post_item: dict, website_settings: dict, event_data: dict) -> any:
        """Downloads raw content and calls the refine agent."""
        
        # Get the input URI from the event data passed to process_request
        raw_article_uri = post_item.get(Constants.RESEARCH_ARTICLE_URI)
        if not raw_article_uri:
             raise ServiceError(f"Missing '{Constants.RESEARCH_ARTICLE_URI}' in input data for refine.", 400, service_name=self.service_name)

        # --- Download Raw Article using S3 Helper ---
        logger.info(f"[{self.service_name}] Downloading raw article from {raw_article_uri}")
        raw_article_text = self.s3_helper.read_text_file(raw_article_uri)
        if raw_article_text is None: # Check if download failed
            raise ServiceError(f"Failed to download raw article from {raw_article_uri}.", 500, service_name=self.service_name)
        
        logger.info(f"[{self.service_name}] Raw article downloaded. Length: {len(raw_article_text)}")

        event_data["raw_article_content"] = raw_article_text

        # Call the selected agent function (which is refine_openai_content)
        return agent_function(
            post_item=post_item,
            website_settings=website_settings,
            event_data=event_data
        )

    def _save_agent_output(self, website_id: str, post_id: str, agent_output: any) -> str | None:
        """Saves the refine agent's text output."""
        if not isinstance(agent_output, str):
             logger.error(f"[{self.service_name}] Agent output was not a string, cannot save.")
             return None 

        # Construct the specific S3 key for the refined article
        s3_key = f"{website_id}/{post_id}/refined_article.txt" # Specific key for refine output
        
        # Call the generic save_text_file method in the helper
        return self.s3_helper.save_text_file( 
            key=s3_key,
            content=agent_output # agent_output is the refined article text string
        )