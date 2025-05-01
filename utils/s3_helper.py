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
            logger.critical("CRITICAL INIT ERROR: CONTENT_BUCKET_NAME environment variable not set.")
            raise ValueError("CONTENT_BUCKET_NAME not configured for S3Helper")
            
        try:
            self.s3_client = boto3.client('s3')
            logger.info(f"S3Helper initialized for bucket: {self.bucket_name}")
        except Exception as e:
            logger.critical("CRITICAL INIT ERROR: Failed to initialize S3 client.")
            raise ValueError("Failed to initialize S3 client") from e

    def save_text_file(self, key: str, content: str) -> str | None:
        """
        Saves text content to a specific key in the configured bucket.
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
        
    def read_text_file(self, s3_uri: str) -> str | None:
        """
        Reads text content from a specific S3 URI.
        """
        logger.info(f"Reading text file from: {s3_uri}")
        try:
            # Basic validation and parsing
            if not s3_uri or not s3_uri.startswith(f"s3://{self.bucket_name}/"):
                logger.error(f"Invalid or incorrect S3 URI format for this bucket: {s3_uri}")
                return None # Or raise ValueError

            # Extract key after "s3://bucket-name/"
            key = s3_uri[len(f"s3://{self.bucket_name}/"):]
            
            logger.debug(f"Downloading from bucket '{self.bucket_name}', key '{key}'")
            s3_object = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            content = s3_object['Body'].read().decode('utf-8')
            logger.info(f"S3 Download successful. Content length: {len(content)}")
            return content
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                 logger.error(f"S3 key not found: s3://{self.bucket_name}/{key}")
            else:
                 logger.exception(f"Failed to download from s3://{self.bucket_name}/{key}")
            return None
        except Exception as e:
            logger.exception(f"An unexpected error occurred during S3 download from key {key}")
            return None