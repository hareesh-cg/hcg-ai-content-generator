import aws_cdk as cdk
from constructs import Construct
import aws_cdk.aws_lambda_python_alpha as lambda_python # Use Python Lambda construct
import aws_cdk.aws_s3 as s3 # Added import for S3
import aws_cdk.aws_dynamodb as dynamodb # Added import for DynamoDB
# Add other imports here as needed (e.g., Step Functions, IAM, API Gateway)
# import aws_cdk.aws_stepfunctions as sfn
# import aws_cdk.aws_stepfunctions_tasks as tasks
# import aws_cdk.aws_iam as iam
# import aws_cdk.aws_apigatewayv2_alpha as apigwv2 # Example for HTTP API
# import aws_cdk.aws_apigatewayv2_integrations_alpha as integrations # Example for HTTP API integrations

import os

class IacStack(cdk.Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # --- 1. Define Core Resources ---

        # S3 Bucket for content storage
        # NOTE: Changed ID to be more descriptive
        content_bucket = s3.Bucket(
            self, "AiContentBucket",
            removal_policy=cdk.RemovalPolicy.RETAIN, # Retain bucket even if stack is deleted (safer for data)
            auto_delete_objects=False, # Change to True ONLY for temporary dev stacks if desired
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL, # Secure default
            encryption=s3.BucketEncryption.S3_MANAGED, # Default encryption
            enforce_ssl=True,
            versioned=False # Enable if you need versioning
        )

        # DynamoDB Table for Posts
        posts_table = dynamodb.Table(
            self, "PostsTable",
            partition_key=dynamodb.Attribute(name="postId", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST, # Suitable for unpredictable load
            removal_policy=cdk.RemovalPolicy.RETAIN # Protect data
        )

        # DynamoDB Table for Website Settings
        website_settings_table = dynamodb.Table(
            self, "WebsiteSettingsTable",
            partition_key=dynamodb.Attribute(name="websiteId", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=cdk.RemovalPolicy.RETAIN
        )

        # --- 2. Handle Secrets ---
        
        # Attempt to get OpenAI key from environment variable (set by CI/CD pipeline)
        openai_key_from_env = os.environ.get("OPENAI_API_KEY_FOR_LAMBDA")

        # Add a warning during synthesis if the key isn't set (won't fail synth)
        if not openai_key_from_env:
            cdk.Annotations.of(self).add_warning(
                "OPENAI_API_KEY_FOR_LAMBDA environment variable not set. Lambdas requiring it may fail at runtime."
            )
        
        # --- 3. Define Lambda Functions (Agents) ---

        # Example: Research Lambda (Agent 1)
        # NOTE: You need to create the actual Lambda code in the specified 'entry' path
        research_lambda = lambda_python.PythonFunction(
            self, "ResearchLambda",
            entry="../lambda_handlers", # ** ADJUST PATH TO YOUR LAMBDA CODE DIRECTORY **
            runtime=cdk.aws_lambda.Runtime.PYTHON_3_11, # Or PYTHON_3_12 etc.
            index="research_handler",       # File containing the handler function
            handler="main",           # Function name to execute
            timeout=cdk.Duration.minutes(5), # Increase timeout for potentially long AI calls
            memory_size=256, # Adjust as needed
            environment={
                "OPENAI_API_KEY": openai_key_from_env if openai_key_from_env else "NOT_SET",
                "CONTENT_BUCKET_NAME": content_bucket.bucket_name,
                # Add other necessary environment variables
            }
        )
        # Grant bucket write permissions
        content_bucket.grant_write(research_lambda)

        # --- Add definitions for your other Lambda functions (Rewrite, Image Prompt, etc.) ---
        # Example Placeholder:
        # rewrite_lambda = lambda_python.PythonFunction(self, "RewriteLambda", ...)
        # image_prompt_lambda = lambda_python.PythonFunction(self, "ImagePromptLambda", ...)
        # image_gen_lambda = lambda_python.PythonFunction(self, "ImageGenLambda", ...)
        # metadata_lambda = lambda_python.PythonFunction(self, "MetadataLambda", ...)
        # markdown_lambda = lambda_python.PythonFunction(self, "MarkdownLambda", ...)
        # trigger_lambda = lambda_python.PythonFunction(self, "TriggerLambda", ...)

        # --- Remember to grant necessary permissions to each Lambda ---
        # e.g., content_bucket.grant_read(rewrite_lambda)
        # e.g., posts_table.grant_read_data(trigger_lambda)
        # e.g., website_settings_table.grant_read_data(trigger_lambda)
        # e.g., trigger_lambda.add_to_role_policy(iam.PolicyStatement(... permissions for stepfunctions:StartExecution ...))


        # --- 4. Define Step Functions State Machine ---
        # (This requires importing sfn and tasks)
        # Example Structure (needs filling in):
        # state_machine = sfn.StateMachine(
        #     self, "AiContentStateMachine",
        #     definition_body=sfn.DefinitionBody.from_chainable(
        #         # Define your state machine steps here using tasks.LambdaInvoke, sfn.Map, etc.
        #         # Example start:
        #         tasks.LambdaInvoke(self, "ResearchStep", lambda_function=research_lambda)
        #         # .next(...) connect the steps
        #     ),
        #     timeout=cdk.Duration.hours(2) # Adjust overall timeout
        # )


        # --- 5. Define API Gateway Trigger ---
        # (Requires importing apigwv2 and integrations)
        # Example Structure (needs filling in):
        # http_api = apigwv2.HttpApi(self, "AiContentApi")
        
        # Example Integration for a trigger lambda:
        # trigger_integration = integrations.HttpLambdaIntegration(
        #     "TriggerIntegration",
        #     handler=trigger_lambda # Assuming you defined trigger_lambda
        # )
        
        # http_api.add_routes(
        #     path="/generate",
        #     methods=[apigwv2.HttpMethod.POST],
        #     integration=trigger_integration
        # )

        # --- 6. Output Useful Information ---
        cdk.CfnOutput(self, "ContentBucketName", value=content_bucket.bucket_name)
        # cdk.CfnOutput(self, "ApiEndpoint", value=http_api.url) # Output API endpoint if defined
        