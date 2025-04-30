# D:\Projects\Python\hcg-ai-content-generator\utils\dynamodb_helper.py
import os
import boto3
from botocore.exceptions import ClientError
import time

from utils.logger_config import get_logger

logger = get_logger(__name__)

class DynamoDBHelper:
    """Handles interactions with DynamoDB tables."""

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
            response = self.posts_table.get_item(Key={'postId': post_id})
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
            response = self.settings_table.get_item(Key={'websiteId': website_id})
            item = response.get('Item')
            if item:
                logger.debug("Website settings found.")
            else:
                logger.debug("Website settings not found.")
            return item
        except ClientError as e:
            logger.error(f"DynamoDB Error getting settings item '{website_id}': {e.response['Error']['Message']}")
            return None

    def update_post_research_uri(self, post_id: str, research_uri: str) -> bool:
        """Updates the Posts table item with the researchArticleUri."""
        logger.info(f"Updating post item '{post_id}' with research URI: {research_uri}")
        try:
            current_timestamp = int(time.time()) # Get current epoch timestamp as integer
            
            self.posts_table.update_item(
                Key={'postId': post_id},
                # Using SET is fine, it adds the attribute if it doesn't exist
                UpdateExpression="SET researchArticleUri = :uri, updateTimestamp = :ts", 
                ExpressionAttributeValues={
                    ':uri': research_uri,
                    # Pass the Python integer directly:
                    ':ts': current_timestamp 
                },
                ReturnValues="NONE" 
            )
            logger.info("Post item updated successfully.")
            return True
        except Exception as e:
            logger.exception(f"Unexpected DynamoDB error updating post item '{post_id}'") # Log exception
            return False
        
    def update_post_status(self, post_id: str, status: str) -> bool:
        """
        Updates the status and updateTimestamp for a post item.
        """
        logger.info(f"Updating status for post item '{post_id}' to: {status}")
        try:
            current_timestamp = int(time.time()) # Get current epoch timestamp as integer

            self.posts_table.update_item(
                Key={'postId': post_id},
                UpdateExpression="SET postStatus = :s, updateTimestamp = :ts", # Use 'postStatus' or just 'status'
                ExpressionAttributeValues={
                    ':s': status,
                    ':ts': current_timestamp
                },
                ReturnValues="NONE"
            )
            logger.info(f"Post item '{post_id}' status updated successfully.")
            return True
        except ClientError as e:
            logger.exception(f"DynamoDB Error updating status for post item '{post_id}'")
            return False
        except Exception as e:
            logger.exception(f"Unexpected error updating status for post item '{post_id}'")
            return False
        