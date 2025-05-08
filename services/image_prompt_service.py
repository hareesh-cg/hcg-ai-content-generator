import os

from services.base_service import BaseContentService 

from utils.logger_config import get_logger
from utils.dynamodb_helper import DynamoDBHelper # For constants AND saving prompts
from utils.s3_helper import S3Helper # To read refined article
from utils.errors import ServiceError
import utils.constants as Constants

from agents.image_prompt_openai import execute as generate_openai_prompts_slugs
from agents.image_slug_openai import generate_slugs_from_prompts as generate_openai_slugs

logger = get_logger(__name__)

class ImagePromptService(BaseContentService): 
    """Orchestrates the image prompt generation process."""

    def __init__(self):
        super().__init__(service_name="ImagePromptService") 

    # --- Implement Abstract Properties ---
    @property
    def status_prefix(self) -> str:
        return "IMAGE_PROMPT"

    @property
    def output_uri_db_key(self) -> str:
        # This service outputs prompts directly to DynamoDB, not an S3 URI
        # We'll use the standard DynamoDB constant for the prompts list
        return Constants.IMAGE_PROMPTS

    # --- Implement Abstract Methods ---
    def _select_agent(self, website_settings: dict, post_item: dict | None = None, previous_step_output: any = None) -> callable:
        """Selects the agent function to call based on settings."""
        # For this service, we always use the OpenAI image prompt agent
        logger.info(f"[{self.service_name}] Selecting OpenAI Image Prompt Agent.")
        return generate_openai_prompts_slugs

    def _call_agent(self, agent_function: callable, post_item: dict, website_settings: dict, event_data: dict) -> any:
        """
        Downloads refined content and calls the image prompt agent.
        Returns a list of dictionaries: [{'prompt': '...', 'slug': '...'}]
        """
        
        refined_article_uri = post_item.get(Constants.REFINED_ARTICLE_URI) 
        if not refined_article_uri:
             post_id = post_item.get(Constants.POST_ID, "Unknown")
             logger.error(f"Missing '{Constants.REFINED_ARTICLE_URI}' in fetched post item for postId '{post_id}'.")
             raise ServiceError(f"Required '{Constants.REFINED_ARTICLE_URI}' not found for postId '{post_id}'. Has the refine step completed successfully?", 400, service_name=self.service_name)
            
        # --- Download Refined Article ---
        logger.info(f"[{self.service_name}] Downloading refined article from {refined_article_uri}")
        refined_article_text = self.s3_helper.read_text_file(refined_article_uri)
        if refined_article_text is None: 
            raise ServiceError(f"Failed to download refined article from {refined_article_uri}.", 500, service_name=self.service_name)
        
        logger.info(f"[{self.service_name}] Refined article downloaded. Length: {len(refined_article_text)}")
        
        event_data["refined_article_content"] = refined_article_text # Add to event data for agent
        # Call the selected agent function
        # Agent returns a list of strings (prompts)
        prompt_list = agent_function(
            post_item=post_item,
            website_settings=website_settings,
            event_data=event_data
        )
        
        if not prompt_list:
             raise ServiceError("Image prompt agent returned no prompts.", 500, service_name=self.service_name)
        logger.info(f"[{self.service_name}] Got {len(prompt_list)} prompts from agent.")

        # --- Step 2: Generate Slugs ---
        logger.info(f"[{self.service_name}] Calling agent to generate slugs...")
        slug_list = generate_openai_slugs(image_prompts=prompt_list) # Call specific agent
        if not slug_list or len(slug_list) != len(prompt_list):
             logger.error(f"Slug generation failed or returned incorrect number of slugs ({len(slug_list)} vs {len(prompt_list)}).")
             raise ServiceError("Failed to generate valid slugs for all prompts.", 500, service_name=self.service_name)
        logger.info(f"[{self.service_name}] Got {len(slug_list)} slugs from agent.")

        # --- Step 3: Combine Prompts and Slugs ---
        combined_data = []
        for prompt, slug in zip(prompt_list, slug_list):
             combined_data.append({"prompt": prompt, "slug": slug})
             
        logger.info(f"[{self.service_name}] Combined prompts and slugs.")
        return combined_data

    def _save_agent_output(self, website_id: str, post_id: str, agent_output: any) -> str | None:
        """Saves the list of image prompts directly to DynamoDB. Returns None as there's no S3 URI."""
        if not isinstance(agent_output, list) or not all(isinstance(d, dict) for d in agent_output):
             logger.error(f"[{self.service_name}] Agent output was not a list of dicts, cannot save prompts/slugs.")
             return None 

        logger.info(f"[{self.service_name}] Saving {len(agent_output)} prompt/slug pairs to DynamoDB for postId {post_id}")
        
        # Save the list of dictionaries under the IMAGE_PROMPTS key
        update_success = self.db_helper.update_post_item(post_id, {Constants.IMAGE_PROMPTS: agent_output})

        if not update_success:
            logger.error(f"[{self.service_name}] Failed to save prompts/slugs to DynamoDB for postId {post_id}.")
            return None 
        
        logger.info(f"[{self.service_name}] Prompt/slug pairs successfully saved to DynamoDB for postId {post_id}.")
        return "DynamoDB_Updated" # Return a non-None placeholder to signal success to base class


    # --- Override Base Class DB Update Method ---
    def _update_db_uri(self, post_id: str, s3_uri: str | None):
        """Overrides the base method because image prompts are saved directly in the item, not to S3."""
        # The actual update (saving the prompt list) happened in _save_agent_output
        # We just log here and do nothing further with the URI field for this specific step.
        if s3_uri == "DynamoDB_Updated": # Check for our success placeholder
             logger.info(f"[{self.service_name}] Image prompts already saved to DynamoDB item for postId {post_id}. Skipping standard URI update.")
        else:
             logger.error(f"[{self.service_name}] _save_agent_output did not indicate successful DynamoDB update for postId {post_id}.")
        # Return success/failure based on the placeholder? Or just assume success if we got here.
        return s3_uri == "DynamoDB_Updated"