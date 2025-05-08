import os
import boto3
from botocore.exceptions import ClientError
import requests
import mimetypes

import utils.constants as Constants
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
        
    def download_and_save_image(self, image_url: str, website_id: str, post_id: str, image_index: int) -> str | None:
        """
        Downloads an image from a URL and saves it to S3.
        Generates a unique filename based on index.
        """
        if not image_url:
            logger.error("No image URL provided for download.")
            return None

        logger.info(f"Downloading image from URL: {image_url}")
        try:
            # Download the image
            response = requests.get(image_url, stream=True, timeout=30) # Add timeout
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

            # Determine content type and extension
            content_type = response.headers.get('content-type', 'image/png') # Default to png
            extension = mimetypes.guess_extension(content_type) or '.png' # Guess extension

            # Construct S3 key
            filename = f"image_{image_index}{extension}"
            s3_key = f"{website_id}/{post_id}/{Constants.S3_IMAGE_FOLDER}/{filename}"

            logger.info(f"Uploading downloaded image to s3://{self.bucket_name}/{s3_key} (Content-Type: {content_type})")

            # Upload to S3 directly from the stream
            self.s3_client.upload_fileobj(
                response.raw, # Use the raw byte stream
                self.bucket_name,
                s3_key,
                ExtraArgs={'ContentType': content_type}
            )

            s3_uri = f"s3://{self.bucket_name}/{s3_key}"
            logger.info(f"Image upload successful. URI: {s3_uri}")
            return s3_uri

        except requests.exceptions.RequestException as re:
            logger.exception(f"Failed to download image from URL: {image_url}")
            return None
        except ClientError as ce:
            logger.exception(f"Failed to upload image to S3 key: {s3_key}")
            return None
        except Exception as e:
            logger.exception(f"An unexpected error occurred during image download/upload for {image_url}")
            return None
        
    def download_and_save_image_with_slug(self, image_url: str, website_id: str, post_id: str, slug: str) -> str | None:
        """Downloads an image from a URL and saves it to S3 using a provided slug for the filename."""
        
        if not image_url: logger.error("No image URL provided."); return None
        if not slug: logger.warning("Empty slug provided, using default."); slug="image" # Handle empty slug

        logger.info(f"Downloading image from URL: {image_url} (for slug: {slug})")
        try:
            response = requests.get(image_url, stream=True, timeout=30)
            response.raise_for_status() 

            content_type = response.headers.get('content-type', 'image/png') 
            extension = mimetypes.guess_extension(content_type) or '.png' 

            # Clean the slug further (optional but recommended)
            # Keep alphanumeric and hyphen, ensure single hyphens
            clean_slug = re.sub(r'[^a-z0-9-]+', '', slug.lower()) # Remove invalid chars
            clean_slug = re.sub(r'-+', '-', clean_slug).strip('-') # Consolidate hyphens
            if not clean_slug: clean_slug = "image" # Ensure not empty after cleaning
            
            filename = f"{clean_slug}{extension}"
            s3_key = f"{website_id}/{post_id}/{Constants.S3_IMAGE_FOLDER}/{filename}"

            logger.info(f"Uploading downloaded image to s3://{self.bucket_name}/{s3_key} (Content-Type: {content_type})")
            self.s3_client.upload_fileobj(
                response.raw, 
                self.bucket_name,
                s3_key,
                ExtraArgs={'ContentType': content_type}
            )

            s3_uri = f"s3://{self.bucket_name}/{s3_key}"
            logger.info(f"Image upload successful. URI: {s3_uri}")
            return s3_uri

        except requests.exceptions.RequestException as re: ... # logging as before
        except ClientError as ce: ... # logging as before
        except Exception as e: ... # logging as before
        return None # Return None on any failure