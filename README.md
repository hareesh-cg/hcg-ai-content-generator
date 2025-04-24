# Serverless AI Content Generation Pipeline (hcg-ai-content-generator)

This project implements an automated, agentic pipeline for generating comprehensive blog articles. It's designed to run entirely on serverless infrastructure within AWS, triggered by a simple HTTP request. The pipeline takes a Post ID, fetches relevant context, uses multiple AI agents for research, writing, image generation, and metadata creation, and finally outputs a complete Markdown file and associated images to cloud storage.

## Features

*   **HTTP Triggered:** Starts the content generation process via an API call.
*   **Context-Aware:** Fetches blog site description, title, and brand settings from DynamoDB.
*   **Agentic Workflow:** Utilizes distinct AI agents for specific tasks:
    *   **Research Agent:** Generates a deeply researched initial draft.
    *   **Refinement Agent:** Rewrites the draft to match brand tone, style, and length constraints.
    *   **Image Prompt Agent:** Suggests relevant image prompts based on the article content.
    *   **Image Generation Agent:** Creates images based on the generated prompts and brand settings.
    *   **Metadata Agent:** Generates SEO-friendly metadata (title, description, keywords).
    *   **Markdown Agent:** Assembles the final article, images, and metadata into a Markdown file.
*   **Asynchronous & Scalable:** Uses AWS Step Functions for robust orchestration of the potentially long-running workflow, leveraging AWS Lambda for scalable, serverless compute.
*   **Configurable:** Website-specific settings (brand tone, article length, colors, etc.) are managed centrally in a DynamoDB table.
*   **Cloud Native:** Built entirely on AWS serverless services (Lambda, Step Functions, API Gateway, S3, DynamoDB, Secrets Manager).
*   **Infrastructure as Code:** Uses AWS CDK (Python) for defining and deploying all necessary cloud resources.

## Architecture Overview

1.  **API Gateway:** Receives an HTTP POST request with a `postId`.
2.  **Trigger Lambda:**
    *   Validates the `postId`.
    *   Fetches the `websiteId` from the `Posts` DynamoDB table.
    *   Fetches the corresponding website settings from the `WebsiteSettings` DynamoDB table.
    *   Initiates the Step Functions state machine execution with the `postId` and settings.
    *   Returns a `202 Accepted` response immediately.
3.  **Step Functions State Machine:** Orchestrates the sequence of tasks:
    *   Calls the **Research Lambda (Agent 1)**.
    *   Calls the **Refinement Lambda (Agent 2)**.
    *   Calls the **Image Prompt Lambda (Agent 3)**.
    *   Uses a **Map State** to call the **Image Generation Lambda (Agent 4)** *in parallel* for each prompt.
    *   Calls the **Metadata Lambda (Agent 5)**.
    *   Calls the **Markdown Assembly Lambda (Agent 6)**.
    *   Handles errors and retries between steps.
    *   Updates the `Posts` table status on completion or failure.
4.  **Task Lambdas (Agents):** Each Lambda function performs its specific AI task, interacting with external AI APIs (like OpenAI, Anthropic, Bedrock, etc.) and using S3 for intermediate storage.
5.  **S3 Bucket:** Stores intermediate artifacts (raw/refined text) and final outputs (images, Markdown file).
6.  **DynamoDB Tables:**
    *   `Posts`: Tracks the status and metadata of each generation request.
    *   `WebsiteSettings`: Stores configuration details for each website/brand.
7.  **Secrets Manager:** Securely stores external AI API keys.

## Technology Stack

*   **Programming Language:** Python 3.9+
*   **Infrastructure as Code:** AWS CDK (Python)
*   **Compute:** AWS Lambda
*   **Orchestration:** AWS Step Functions (Standard Workflows)
*   **API Layer:** AWS API Gateway (HTTP API)
*   **Storage:** AWS S3
*   **Database:** AWS DynamoDB
*   **Secrets Management:** AWS Secrets Manager
*   **AI Services:** (Placeholders - requires integration)
    *   Text Generation: OpenAI GPT-4/GPT-3.5, Anthropic Claude, AWS Bedrock, Azure OpenAI, etc.
    *   Image Generation: OpenAI DALL-E 3, Stability AI, AWS Bedrock Titan Image, etc.

## Prerequisites

*   AWS Account
*   AWS CLI configured with credentials (`aws configure`)
*   Node.js and npm (Required by AWS CDK CLI)
*   AWS CDK CLI (`npm install -g aws-cdk`)
*   Python 3.9 or later
*   Access keys for desired AI APIs (e.g., OpenAI API Key)

## Setup & Installation

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd hcg-ai-content-generator
    ```
2.  **Navigate to the CDK directory:**
    ```bash
    cd iac
    ```
3.  **Create and activate Python virtual environment:**
    ```bash
    # Ensure python3.x-venv package is installed (e.g., sudo apt install python3.12-venv)
    python3 -m venv .venv
    source .venv/bin/activate
    ```
4.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    # Install specific AWS service construct libraries (if not already frozen in requirements.txt)
    pip install aws-cdk.aws-lambda aws-cdk.aws-stepfunctions aws-cdk.aws-stepfunctions-tasks aws-cdk.aws-s3 aws-cdk.aws-dynamodb aws-cdk.aws-apigatewayv2 aws-cdk.aws-iam aws-cdk.aws-secretsmanager aws-cdk.aws-logs 
    ```

## Configuration

1.  **AWS Credentials:** Ensure your AWS CLI is configured with credentials that have permissions to deploy CDK stacks (CloudFormation, Lambda, IAM, S3, DynamoDB, API Gateway, Step Functions, Secrets Manager). See Phase 0 notes on IAM setup.

2.  **AI API Keys:**
    *   Store your necessary AI API keys (e.g., OpenAI key) securely in **AWS Secrets Manager**.
    *   Choose a consistent name for your secret (e.g., `AiContentPipelineKeys`).
    *   Structure the secret as key-value pairs (e.g., `{"OpenAI_ApiKey": "sk-..."}` ).
    *   Update the CDK stack (`iac/iac_stack.py`) to reference this secret name when granting Lambda functions access and passing the secret ARN/name as an environment variable.

3.  **DynamoDB `WebsiteSettings` Table:**
    *   After deployment (`cdk deploy`), this table will be created but will be empty.
    *   You **must manually populate** this table with entries for each website profile you want to manage. Use the `websiteId` as the primary key.
    *   Key attributes to populate include: `websiteId`, `websiteName`, `websiteDescription`, `brandTone`, `articleLengthMin`, `articleLengthMax`, `brandColors`, `imageStylePrompt`, etc. (Refer to the schema defined in Phase 0).

4.  **(Optional) CDK Context:** You might configure AWS Account ID and Region in `cdk.json` or via environment variables if needed, although the CDK typically infers these from your AWS CLI profile.

## Deployment

1.  **Bootstrap CDK (If first time in region/account):**
    ```bash
    # Ensure virtual environment is active and you are in the 'iac' directory
    cdk bootstrap aws://<YOUR_AWS_ACCOUNT_ID>/<YOUR_AWS_REGION>
    ```
2.  **Synthesize (Optional):** Check the CloudFormation template that will be generated:
    ```bash
    cdk synth
    ```
3.  **Deploy the Stack:**
    ```bash
    cdk deploy
    ```
    *   The CDK will show you the changes (especially IAM changes) and ask for confirmation before deploying.
    *   Deployment will create all the defined AWS resources. Note the API Gateway endpoint URL output at the end.

## Usage

1.  **Prepare Data:**
    *   Ensure the `WebsiteSettings` table contains an entry for the `websiteId` associated with your target post.
    *   Ensure your `Posts` table contains an entry with the `postId` you want to generate, and that it includes the correct `websiteId`. (The trigger lambda assumes this entry exists to retrieve the `websiteId`).
2.  **Trigger the Pipeline:**
    *   Find the API Gateway endpoint URL from the `cdk deploy` output. It will look something like `https://xxxxxxxxx.execute-api.us-east-1.amazonaws.com/`.
    *   Send an HTTP POST request to this URL (or the specific path configured, e.g., `/generate`).
    *   The request body should be JSON containing the `postId`:
        ```json
        {
          "postId": "your-unique-post-id-123"
        }
        ```
    *   You can use tools like `curl`, Postman, or integrate this into another application.
        ```bash
        curl -X POST \
          https://<your-api-id>.execute-api.<your-region>.amazonaws.com/generate \
          -H 'Content-Type: application/json' \
          -d '{
            "postId": "your-unique-post-id-123"
          }'
        ```
3.  **Monitor Execution:**
    *   The API will return a `202 Accepted` immediately.
    *   You can monitor the execution progress in the AWS Step Functions console for your state machine.
    *   Check the status field in the `Posts` DynamoDB table.
4.  **Retrieve Output:**
    *   Upon successful completion, the final Markdown file and generated images will be stored in the configured S3 bucket, typically under a path like `s3://<your-content-bucket>/posts/<postId>/`.

## Cleanup

To remove all deployed resources, destroy the CDK stack:

```bash
# Ensure virtual environment is active and you are in the 'iac' directory
cdk destroy
```

## License
(MIT License). Defaults to LICENSE file if present.