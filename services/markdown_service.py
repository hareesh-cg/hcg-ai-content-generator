# D:\Projects\Python\hcg-ai-content-generator\services\markdown_service.py
import os

from services.base_service import BaseContentService

from utils.logger_config import get_logger
from utils.errors import ServiceError
from utils import constants as Constants

from agents.markdown_assembler import execute as assemble_markdown # Import agent

logger = get_logger(__name__)

class MarkdownService(BaseContentService): 
    """Orchestrates the final Markdown assembly process."""

    def __init__(self):
        super().__init__(service_name="MarkdownService") 

    # --- Implement Abstract Properties ---
    @property
    def status_prefix(self) -> str:
        return "MARKDOWN"

    @property
    def output_uri_db_key(self) -> str:
        return Constants.MARKDOWN_URI 

    # --- Implement Abstract Methods ---

    def _select_agent(self, website_settings: dict, post_item: dict | None = None, previous_step_output: any = None) -> callable:
        """Selects the markdown assembly agent."""
        logger.info(f"[{self.service_name}] Selecting Markdown Assembler agent.")
        return assemble_markdown 

    def _call_agent(self, agent_function: callable, post_item: dict, website_settings: dict, event_data: dict) -> any:
        """Downloads refined content and calls the markdown agent."""
        
        refined_article_uri = post_item.get(Constants.REFINED_ARTICLE_URI) 
        if not refined_article_uri:
            raise ServiceError(f"Missing '{Constants.REFINED_ARTICLE_URI}' in post item.", 400, service_name=self.service_name)
            
        # --- Download Refined Article ---
        logger.info(f"[{self.service_name}] Downloading refined article from {refined_article_uri}")
        refined_article_text = self.s3_helper.read_text_file(refined_article_uri)
        if refined_article_text is None: 
            raise ServiceError(f"Failed to download refined article from {refined_article_uri}.", 500, service_name=self.service_name)
        
        logger.info(f"[{self.service_name}] Refined article downloaded.")

        # Prepare event_data for the agent
        event_data["refined_article_content"] = refined_article_text

        # Call the selected agent function
        # Agent returns the full markdown string
        markdown_content = agent_function(
            post_item=post_item, # Pass post_item for metadata, image URIs, title
            website_settings=website_settings, # Pass settings for potential formatting notes
            event_data=event_data
        )
        
        # Return the markdown string
        return markdown_content


    def _save_agent_output(self, website_id: str, post_id: str, agent_output: any) -> str | None:
        """Saves the final markdown content to S3."""
        if not isinstance(agent_output, str):
             logger.error(f"[{self.service_name}] Agent output was not a string, cannot save markdown.")
             return None

        # Construct the specific S3 key for the markdown file
        s3_key = f"{website_id}/{post_id}/{Constants.S3_MARKDOWN_FILENAME}" 
        
        # Call the generic save_text_file method in the helper
        # Note: ContentType should be 'text/markdown' for better compatibility
        s3_uri = self.s3_helper.save_text_file(
            key=s3_key,
            content=agent_output, # agent_output is the markdown string
            # content_type='text/markdown' # TODO: Add optional content_type to s3_helper.save_text_file
        )

        if not s3_uri:
            logger.error(f"[{self.service_name}] Failed to save final markdown file to S3 for postId {post_id}.")
            return None
            
        logger.info(f"[{self.service_name}] Final markdown saved successfully to: {s3_uri}")
        return s3_uri