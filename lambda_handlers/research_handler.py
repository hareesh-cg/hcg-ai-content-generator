import json
import os
# Import the specific agent implementation
from agents.research_openai import generate_research_draft 
# If you later add research_gemini, you could add logic here to choose based on env var or config

print("Research Handler Lambda Initialized")

# Get bucket name from environment variable once
bucket_name = os.environ.get('CONTENT_BUCKET_NAME')

def main(event, context):
    """
    AWS Lambda handler for the research step.
    Calls the appropriate research agent.
    """
    print("Received event:", json.dumps(event, indent=2))

    if not bucket_name:
         print("Error: CONTENT_BUCKET_NAME environment variable not set.")
         # Fail the invocation cleanly
         raise ValueError("CONTENT_BUCKET_NAME not configured") 

    try:
        # Extract data needed by the agent function
        post_id = event.get('postId')
        blog_title = event.get('blogTitle')
        website_settings = event.get('websiteSettings', {})

        # Call the agent function
        # Note: OPENAI_API_KEY is used internally by the agent module now
        s3_uri = generate_research_draft(
            post_id=post_id,
            blog_title=blog_title,
            website_settings=website_settings,
            bucket_name=bucket_name
        )

        # Prepare output for Step Functions, including the result from the agent
        output = {
            'postId': post_id,
            'blogTitle': blog_title,
            'websiteSettings': website_settings,
            'rawArticleUri': s3_uri # Pass the result from the agent
        }
        
        # Return the dictionary directly for Step Functions state
        return output

    except Exception as e:
        print(f"Error processing event for Post ID {post_id}: {e}")
        # Raise the exception to signal failure to Step Functions
        raise e