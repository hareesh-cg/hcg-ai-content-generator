import os
import sys
from dotenv import load_dotenv # Install using: pip install python-dotenv

# Add project root to path to allow imports like 'from services...'
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Load environment variables from a .env file (optional but recommended)
# Create a .env file in the project root with lines like:
load_dotenv() 

# Now import your service AFTER loading env vars
from utils.errors import ServiceError
from utils.logger_config import setup_logging # Ensure logging is set up

from services.research_service import ResearchService
from services.refine_service import RefineService
from services.image_prompt_service import ImagePromptService
from services.image_gen_service import ImageGenService
from services.metadata_service import MetadataService

# --- Test Configuration ---
TEST_WEBSITE_ID = "my-test-blog-v1" # Use an ID that exists in your DynamoDB
TEST_POST_ID = "test-post-001"    # Use an ID that exists in your DynamoDB

def test_function(test_service: object) -> None:
    """A simple test function to demonstrate the test structure."""

    event_data = {
            "postId": TEST_POST_ID,
            "websiteId": TEST_WEBSITE_ID
        }
    
    print(f"Testing {test_service.__class__.__name__} with postId: {TEST_POST_ID} and websiteId: {TEST_WEBSITE_ID}")
    result = test_service.process_request(event_data)
    print("\n--- Test Result ---")
    print(f"Success: {result}")

if __name__ == "__main__":
    setup_logging() # Set up logging based on LOG_LEVEL env var

    try:
        # test_function(ResearchService())
        # test_function(RefineService())
        # test_function(ImagePromptService())
        # test_function(ImageGenService())
        test_function(MetadataService())

    except ServiceError as se:
        print(f"\n--- Test Failed (ServiceError) ---")
        print(f"Status Code: {se.status_code}")
        print(f"Message: {se.message}")
        print(f"Service: {se.service_name}")
        print(f"Details: {se.details}")
    except Exception as e:
        print(f"\n--- Test Failed (Unexpected Error) ---")
        import traceback
        traceback.print_exc()

    print("\n--- Test Complete ---")
