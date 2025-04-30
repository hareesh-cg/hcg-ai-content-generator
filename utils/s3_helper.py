import os
import boto3
from botocore.exceptions import ClientError
from utils.logger_config import get_logger # Use the logger helper

logger = get_logger(__name__)

class S3Helper:
    """Handles interactions with the S3 bucket for blog content."""

    def __init__(self):
        """Initializes the helper and S3 client."""
        self.bucket_name = os.environ.get('CONTENT_BUCKET_NAME')
        if not self.bucket_name:
            logger.error("CRITICAL INIT ERROR: CONTENT_BUCKET_NAME environment variable not set.")
            raise ValueError("CONTENT_BUCKET_NAME not configured for S3Helper")
            
        try:
            self.s3_client = boto3.client('s3')
            logger.info(f"S3Helper initialized for bucket: {self.bucket_name}")
        except Exception as e:
            logger.exception("CRITICAL INIT ERROR: Failed to initialize S3 client.")
            raise ValueError("Failed to initialize S3 client") from e

    def save_text_file(self, key: str, content: str) -> str | None:
        """
        Saves text content to a specific key in the configured bucket.

        Args:
            key: The full S3 key (path within the bucket).
            content: The string content to save.

        Returns:
            The S3 URI of the saved object, or None if upload failed.
        """
        logger.info(f"Uploading text file to s3://{self.bucket_name}/{key}")
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=content.encode('utf-8'),
                ContentType='text/plain'
            )
            s3_uri = f"s3://{self.bucket_name}/{key}"
            logger.info(f"S3 Upload successful. URI: {s3_uri}")
            return s3_uri
        except ClientError as e:
            logger.exception(f"Failed to upload to s3://{self.bucket_name}/{key}")
            return None
        except Exception as e:
            logger.exception(f"An unexpected error occurred during S3 upload to key {key}")
            return None