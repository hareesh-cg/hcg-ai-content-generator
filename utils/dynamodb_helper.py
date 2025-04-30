# D:\Projects\Python\hcg-ai-content-generator\utils\dynamodb_helper.py
import os
import boto3
from botocore.exceptions import ClientError

class DynamoDBHelper:
    """Handles interactions with DynamoDB tables."""

    def __init__(self):
        """Initializes the helper and table resources."""
        self.posts_table_name = os.environ.get('POSTS_TABLE_NAME')
        self.settings_table_name = os.environ.get('SETTINGS_TABLE_NAME')

        if not self.posts_table_name or not self.settings_table_name:
            raise ValueError("Missing DynamoDB table name environment variables (POSTS_TABLE_NAME, SETTINGS_TABLE_NAME)")

        try:
            dynamodb_resource = boto3.resource('dynamodb')
            self.posts_table = dynamodb_resource.Table(self.posts_table_name)
            self.settings_table = dynamodb_resource.Table(self.settings_table_name)
            print(f"DynamoDBHelper initialized for tables: {self.posts_table_name}, {self.settings_table_name}")
        except Exception as e:
            print(f"Error initializing DynamoDB resources: {e}")
            raise ValueError("Failed to initialize DynamoDB table resources") from e

    def get_post(self, post_id: str) -> dict | None:
        """Gets an item from the Posts table by postId."""
        print(f"Getting post item with postId: {post_id}")
        try:
            response = self.posts_table.get_item(Key={'postId': post_id})
            item = response.get('Item')
            if item:
                print("Post item found.")
            else:
                print("Post item not found.")
            return item
        except ClientError as e:
            print(f"DynamoDB Error getting post item '{post_id}': {e.response['Error']['Message']}")
            # Depending on desired behavior, you might return None or raise an exception
            return None # Returning None indicates not found or error

    def get_website_settings(self, website_id: str) -> dict | None:
        """Gets an item from the WebsiteSettings table by websiteId."""
        print(f"Getting website settings with websiteId: {website_id}")
        try:
            response = self.settings_table.get_item(Key={'websiteId': website_id})
            item = response.get('Item')
            if item:
                print("Website settings found.")
            else:
                print("Website settings not found.")
            return item
        except ClientError as e:
            print(f"DynamoDB Error getting settings item '{website_id}': {e.response['Error']['Message']}")
            return None

    def update_post_research_uri(self, post_id: str, research_uri: str) -> bool:
        """Updates the Posts table item with the researchArticleUri."""
        print(f"Updating post item '{post_id}' with research URI: {research_uri}")
        try:
            self.posts_table.update_item(
                Key={'postId': post_id},
                UpdateExpression="SET researchArticleUri = :uri, updateTimestamp = :ts",
                ExpressionAttributeValues={
                    ':uri': research_uri,
                    ':ts': boto3.dynamodb.types.NUMBER.Number(int(__import__('time').time())) # Add an update timestamp
                },
                ReturnValues="NONE" # Don't need updated attributes back
            )
            print("Post item updated successfully.")
            return True
        except ClientError as e:
            print(f"DynamoDB Error updating post item '{post_id}': {e.response['Error']['Message']}")
            return False