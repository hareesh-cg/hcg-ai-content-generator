import os
from utils.logger_config import get_logger
# Import base class, helpers, errors
from services.base_service import BaseContentService 
from utils.dynamodb_helper import DynamoDBHelper # Still need constants
from utils.s3_helper import S3Helper
from utils.errors import ServiceError 
# Import the specific agent implementation
from agents.research_openai import generate_research_draft as generate_openai_draft 

logger = get_logger(__name__)
SERVICE_NAME = "ResearchService"

class ResearchService(BaseContentService): # Inherit from base
    """Orchestrates the research article generation process."""

    def __init__(self):
        # Initialize the base class, passing the service name
        super().__init__(service_name=SERVICE_NAME)

    # --- Implement Abstract Properties ---
    @property
    def status_prefix(self) -> str:
        return "RESEARCH"

    @property
    def output_uri_db_key(self) -> str:
        # The DynamoDB attribute name for this service's output URI
        return DynamoDBHelper.RESEARCH_ARTICLE_URI

    # --- Implement Abstract Methods ---

    def _select_agent(self, website_settings: dict, post_item: dict | None = None, previous_step_output: any = None) -> callable:
        """Selects the research agent."""
        # TODO: Add logic if multiple research agents exist (e.g., check settings)
        logger.info(f"[{self.service_name}] Selecting OpenAI agent.")
        return generate_openai_draft # Return the function object

    def _call_agent(self, agent_function: callable, post_item: dict, website_settings: dict, previous_step_output: any = None) -> any:
        """Calls the research agent."""
        blog_title = post_item.get(DynamoDBHelper.BLOG_TITLE)
        if not blog_title:
            raise ServiceError(f"Missing '{DynamoDBHelper.BLOG_TITLE}' in post item.", 500, service_name=self.service_name)
            
        # Call the selected agent function (which is generate_openai_draft in this case)
        return agent_function(
            blog_title=blog_title,
            website_settings=website_settings
        )

    def _save_agent_output(self, website_id: str, post_id: str, agent_output: any) -> str | None:
        """Saves the research agent's text output."""
        if not isinstance(agent_output, str):
             logger.error(f"[{self.service_name}] Agent output was not a string, cannot save.")
             return None # Or raise error

        # Construct the specific S3 key for the research article
        s3_key = f"{website_id}/{post_id}/research_article.txt" 
        
        # Call the generic save_text_file method in the helper
        return self.s3_helper.save_text_file( 
            key=s3_key,
            content=agent_output # agent_output is the raw article text string
        )