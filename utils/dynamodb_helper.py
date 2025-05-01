import os
import boto3
from botocore.exceptions import ClientError
import time

from utils.logger_config import get_logger

logger = get_logger(__name__)

class DynamoDBHelper:
    """Handles interactions with DynamoDB tables."""

    POST_ID = "postId" # Partition Key
    BLOG_TITLE = "blogTitle"
    POST_STATUS = "postStatus" # Status field
    RESEARCH_ARTICLE_URI = "researchArticleUri"
    REFINED_ARTICLE_URI = "refinedArticleUri"
    MARKDOWN_URI = "markdownUri"
    IMAGE_PROMPTS = "imagePrompts"
    IMAGE_URIS = "imageUris"
    METADATA = "metadata"
    UPDATE_TIMESTAMP = "updateTimestamp"

    # Website Settings Table Attributes
    WEBSITE_ID = "websiteId" # Partition Key

    def __init__(self):
        """Initializes the helper and table resources."""
        self.posts_table_name = os.environ.get('POSTS_TABLE_NAME')
        self.settings_table_name = os.environ.get('SETTINGS_TABLE_NAME')

        if not self.posts_table_name or not self.settings_table_name:
            logger.error("Missing DynamoDB table name environment variables")
            raise ValueError("Missing DynamoDB table name environment variables (POSTS_TABLE_NAME, SETTINGS_TABLE_NAME)")

        try:
            dynamodb_resource = boto3.resource('dynamodb')
            self.posts_table = dynamodb_resource.Table(self.posts_table_name)
            self.settings_table = dynamodb_resource.Table(self.settings_table_name)
            logger.info(f"DynamoDBHelper initialized for tables: {self.posts_table_name}, {self.settings_table_name}")
        except Exception as e:
            logger.error(f"Error initializing DynamoDB resources: {e}")
            raise ValueError("Failed to initialize DynamoDB table resources") from e

    def get_post(self, post_id: str) -> dict | None:
        """Gets an item from the Posts table by postId."""
        logger.info(f"Getting post item with postId: {post_id}")
        try:
            response = self.posts_table.get_item(Key={self.POST_ID: post_id})
            item = response.get('Item')
            if item:
                logger.debug("Post item found.")
            else:
                logger.debug("Post item not found.")
            return item
        except ClientError as e:
            logger.error(f"DynamoDB Error getting post item '{post_id}': {e.response['Error']['Message']}")
            return None

    def get_website_settings(self, website_id: str) -> dict | None:
        """Gets an item from the WebsiteSettings table by websiteId."""
        logger.info(f"Getting website settings with websiteId: {website_id}")
        try:
            response = self.settings_table.get_item(Key={self.WEBSITE_ID: website_id})
            item = response.get('Item')
            if item:
                logger.debug("Website settings found.")
            else:
                logger.debug("Website settings not found.")
            return item
        except ClientError as e:
            logger.error(f"DynamoDB Error getting settings item '{website_id}': {e.response['Error']['Message']}")
            return None

    def update_post_item(self, post_id: str, attributes_to_update: dict) -> bool:
        """
        Updates attributes for a specific post item in the Posts table.
        Automatically adds/updates the 'updateTimestamp' attribute.
        """
        if not attributes_to_update:
            logger.warning(f"No attributes provided to update for postId: {post_id}")
            return True # Nothing to update is not an error

        logger.info(f"Updating post item '{post_id}' with attributes: {list(attributes_to_update.keys())}")

        # Add updateTimestamp automatically
        attributes_to_update[self.UPDATE_TIMESTAMP] = int(time.time())

        # Construct UpdateExpression and ExpressionAttributeValues dynamically
        update_expression_parts = []
        expression_attribute_values = {}
        expression_attribute_names = {}

        for i, (key, value) in enumerate(attributes_to_update.items()):
            value_placeholder = f":v{i}"
            # Check if key is a reserved word - use name placeholder if needed
            # A simple check (not exhaustive):
            is_reserved = key.upper() in ["STATUS", "DATA", "KEY", "VALUE", "NAME"] # Add more if needed
            
            if is_reserved:
                name_placeholder = f"#k{i}"
                update_expression_parts.append(f"{name_placeholder} = {value_placeholder}")
                expression_attribute_names[name_placeholder] = key
            else:
                update_expression_parts.append(f"{key} = {value_placeholder}")
                
            expression_attribute_values[value_placeholder] = value

        update_expression = "SET " + ", ".join(update_expression_parts)

        try:
            update_kwargs = {
                'Key': {self.POST_ID: post_id},
                'UpdateExpression': update_expression,
                'ExpressionAttributeValues': expression_attribute_values,
                'ReturnValues': "NONE"
            }
            
            logger.debug(f"DynamoDB update_item args for {post_id}: {update_kwargs}") # Log arguments for debug
            
            self.posts_table.update_item(**update_kwargs)

            logger.info(f"Post item '{post_id}' updated successfully.")
            return True
        except ClientError as e:
            logger.exception(f"DynamoDB Error updating post item '{post_id}' : {e}")
            return False
        except Exception as e:
            logger.exception(f"Unexpected error updating post item '{post_id}' : {e}")
            return False
        