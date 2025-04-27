import aws_cdk as cdk
from constructs import Construct
import aws_cdk.aws_lambda_python_alpha as lambda_python # Use Python Lambda construct
import os # Needed to read environment variables potentially set by CI/CD

# --- Inside the IacStack class ---

# Attempt to get keys from GitHub Secrets (passed via env at deployment time)
# This relies on the CI/CD runner *setting* these env vars before calling 'cdk deploy'
# (You might need to add 'env:' section to the 'CDK Deploy' step in deploy.yml)
openai_key_from_env = os.environ.get("OPENAI_API_KEY_FOR_LAMBDA") 
# Note: We add _FOR_LAMBDA to distinguish from potential workflow secrets

# Define your Lambda function(s)
research_lambda = lambda_python.PythonFunction(
    self, "ResearchLambda",
    entry="path/to/your/lambda/code", # Point to the DIRECTORY containing lambda code
    runtime=cdk.aws_lambda.Runtime.PYTHON_3_11,
    index="handler.py", # Your main python file
    handler="main",     # The function name within that file
    environment={
        # Inject the secret from environment variable into the Lambda's environment
        "OPENAI_API_KEY": openai_key_from_env if openai_key_from_env else "DUMMY_KEY_FOR_SYNTH",
        # Add other environment variables
        "BUCKET_NAME": content_bucket.bucket_name, 
        # etc.
    }
)
# Handle cases where the key isn't present during local synth/testing
if not openai_key_from_env:
    cdk.Annotations.of(self).add_warning(
        "OPENAI_API_KEY_FOR_LAMBDA environment variable not set. Lambda may fail at runtime."
    )

# Add permissions for the lambda...