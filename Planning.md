**Project Title:** Serverless AI Content Generation Pipeline
**Goal:** Create an automated, asynchronous pipeline triggered by an HTTP request to generate comprehensive, brand-aligned blog articles with images and metadata, storing the results in cloud storage.
**Chosen Language:** Python 3.9+ (Widely supported on Lambda/Azure Functions, excellent AI/ML ecosystem)
**Target Cloud:** (Let's assume AWS for specifics, but note Azure equivalents)
-   **Compute:** AWS Lambda
-   **Orchestration:** AWS Step Functions (Standard Workflow)
-   **API:** AWS API Gateway (HTTP API or REST API)
-   **Database:** AWS DynamoDB
-   **Storage:** AWS S3
-   **Secrets:** AWS Secrets Manager
-   **Monitoring:** AWS CloudWatch
-   **(Azure Equivalents):** Azure Functions, Azure Durable Functions, Azure API Management/Functions HTTP Trigger, Azure Cosmos DB, Azure Blob Storage, Azure Key Vault, Azure Monitor
    
**Key Libraries/SDKs:**
-   boto3: AWS SDK for Python (interacting with Lambda, Step Functions, S3, DynamoDB, Secrets Manager)
-   openai / anthropic / Azure SDKs: For interacting with chosen LLM and Image Generation APIs.
-   requests: For potential generic HTTP calls.
-   **(Optional but Recommended):**  langchain or semantic-kernel: To potentially simplify prompt management, LLM interaction, and chaining within functions.
-   **(Optional):** AWS Serverless Application Model (SAM) or AWS Cloud Development Kit (CDK) for Infrastructure as Code.
    
----------
**Project Phases & Plan:**
**Phase 0: Foundation & Setup (Week 1)**
1.  **Cloud Environment Setup:**
    -   Configure AWS Account.
    -   Set up IAM User/Role for deployment with necessary permissions.
2.  **Local Development Environment:**
    -   Install Python 3.9+.
    -   Set up virtual environments (venv).
    -   Configure AWS CLI/SDK credentials locally.
    -   Choose IDE (e.g., VS Code with Python extensions).
3.  **Infrastructure as Code (IaC) Setup:**
    -   Choose IaC tool (e.g., AWS SAM or CDK). Strongly recommended over manual setup.
    -   Initialize IaC project.
    -   Define core resources:
        -   **S3 Bucket:** For storing raw articles, refined articles, images, final markdown. Structure with prefixes (e.g., /posts/{postId}/raw_article.txt).
        -   **DynamoDB Tables:**
            -   Posts: postId (Partition Key, String), websiteId (String), status (String - e.g., "pending", "processing", "generating_images", "complete", "failed"), finalMarkdownUri (String, optional), executionArn (String, optional), createdAt, updatedAt.
            -   WebsiteSettings: websiteId (Partition Key, String), websiteName, websiteDescription, brandTone, targetAudience, articleLengthMin, articleLengthMax, brandColors (List of Strings, e.g., ["#FF5733", "#33FF57"]), imageStylePrompt, imageAspectRatio, negativeImagePrompts, coreKeywords, seoInstructions, markdownFormattingNotes, preferredTextModel, preferredImageModel, additionalContext, isActive (Boolean), createdAt, updatedAt.
        -   **Secrets Manager:** Store AI API Keys (OpenAI, Anthropic, Azure OpenAI Key, etc.).
        -   **IAM Roles:** Define execution roles for Lambda functions and Step Functions state machine with least-privilege access to S3, DynamoDB, Secrets Manager, CloudWatch Logs, and potentially external AI service APIs.
4.  **Version Control:**
    -   Initialize Git repository.
    -   Establish branching strategy (e.g., main, develop, feature branches).
5.  **Project Structure:**
    -   Organize code logically (e.g., src/handlers/, src/utils/, tests/, template.yaml or cdk_stack.py).
    -   Set up requirements.txt for dependencies.
        
**Phase 1: Core Agent Function Development (Weeks 2-4)**
Develop each function independently first, mocking inputs/outputs.
1.  **Function 1: Research & Draft Generation (Agent 1)**
    -   Input: blogTitle, blogDescription, websiteSettings (subset: description, audience, keywords, context).
    -   Logic: Construct detailed prompt, call chosen LLM API (e.g., GPT-4 via OpenAI/Azure), handle response/errors, save raw text to S3.
    -   Output: { "rawArticleUri": "s3://..." }
    -   Testing: Unit tests mocking LLM API and S3 upload.
2.  **Function 2: Rewrite & Refine (Agent 2)**
    -   Input: rawArticleUri, websiteSettings (subset: brandTone, lengthMin, lengthMax, audience).
    -   Logic: Download raw article, construct rewrite prompt, call LLM, handle response/errors, save refined text to S3.
    -   Output: { "refinedArticleUri": "s3://..." }
    -   Testing: Unit tests mocking S3 download, LLM API, S3 upload.
3.  **Function 3: Image Prompt Generation (Agent 3)**
    -   Input: refinedArticleUri, websiteSettings (subset: imageStylePrompt, maybe brandColors for context).
    -   Logic: Download refined article, construct prompt for LLM to suggest image ideas/prompts, parse response.
    -   Output: { "imagePrompts": ["detailed prompt 1...", "detailed prompt 2..."] }
    -   Testing: Unit tests mocking S3 download, LLM API.
4.  **Function 4: Image Generation (Agent 4)**
    -   Input: Single imagePrompt, websiteSettings (subset: brandColors, imageStylePrompt, aspectRatio, negativePrompts, preferredImageModel).
    -   Logic: Enhance prompt with style/color info, call Image Generation API (e.g., DALL-E 3), handle response/errors, save image to S3 (unique name).
    -   Output: { "imageUrl": "s3://..." }
    -   Testing: Unit tests mocking Image API and S3 upload.
5.  **Function 5: Metadata Generation (Agent 5)**
    -   Input: refinedArticleUri, blogTitle, websiteSettings (subset: seoInstructions, coreKeywords, websiteName).
    -   Logic: Download refined article, construct prompt for LLM to generate metadata, parse response.
    -   Output: { "metadata": { ... } }
    -   Testing: Unit tests mocking S3 download, LLM API.
6.  **Function 6: Markdown Assembly (Agent 6)**
    -   Input: refinedArticleUri, imageUrls (list), metadata, websiteSettings (subset: markdownFormattingNotes).
    -   Logic: Download refined text, strategically insert image Markdown (![alt text](imageUrl) - determine alt text simply or via another LLM call?), prepend metadata (e.g., as front matter), apply formatting notes, save final .md file to S3.
    -   Output: { "finalMarkdownUri": "s3://..." }
    -   Testing: Unit tests mocking S3 download, testing markdown generation logic, S3 upload.
7.  **Utility/Shared Code:** Develop shared code for S3 interactions, DynamoDB interactions, fetching secrets, common error handling, logging setup.
    
**Phase 2: Orchestration with Step Functions (Week 5)**
1.  **Define State Machine (using IaC - SAM/CDK):**
    -   Define states corresponding to each Lambda function.
    -   Pass data between states correctly (using ResultPath, Parameters, ensuring only necessary data/URIs are passed).
    -   Implement Map state for parallel image generation (iterating over imagePrompts, collecting imageUrls).
    -   Configure error handling (Catch blocks) and retry logic (Retry blocks) for transient errors (e.g., API timeouts).
    -   Define final success/failure states.
2.  **Integrate Lambda Functions:** Link the defined Lambda functions to the corresponding Task states in the state machine definition.
3.  **Update IAM Permissions:** Ensure the Step Functions state machine role has lambda:InvokeFunction permissions for all task functions.
4.  **Initial Orchestration Testing:** Trigger the state machine manually (via AWS Console or CLI) with sample input and verify flow and data passing. Debug using Step Functions execution history.
    
**Phase 3: API Trigger & End-to-End Flow (Week 6)**
1.  **API Gateway Setup (using IaC):**
    -   Define HTTP API or REST API endpoint (e.g., POST /generate).
    -   Configure request validation (ensure postId is present).
    -   (Optional) Add basic authentication/authorization (e.g., API Key, IAM Auth, Lambda Authorizer).
2.  **Trigger Lambda Function:**
    -   Create a new Lambda function (TriggerGenerateFunction).
    -   Input: API Gateway event (containing postId in body).
    -   Logic:
        -   Validate postId.
        -   Query Posts table for websiteId. Handle post not found.
        -   Query WebsiteSettings table for settings using websiteId. Handle settings not found or inactive.
        -   Update Posts table status to "pending" or "submitted".
        -   Construct initial input payload for Step Functions (postId, settings object, blog title/desc if fetched here).
        -   Start Step Functions execution (boto3.client('stepfunctions').start_execution(...)).
        -   Update Posts table with executionArn.
        -   Return 202 Accepted response with executionArn or a tracking ID.
    -   Link API Gateway endpoint to this Lambda function.
3.  **Status Update Logic (within Orchestration):**
    -   (Optional but Recommended) Add Lambda Task states within Step Functions at key milestones (e.g., after rewrite, before/after image generation) to update the status field in the Posts DynamoDB table.
    -   Add a final step in the State Machine (on success) to update the Posts table status to "complete" and store finalMarkdownUri. Handle failure paths to set status to "failed".
4.  **(Optional) Status Check Endpoint:**
    -   Create a GET /generate/status/{executionArn} endpoint linked to a new Lambda.
    -   Lambda fetches execution status/history from Step Functions (describe_execution) and/or reads status from the Posts table.
    -   Returns current status and potentially output URIs upon completion.
5.  **End-to-End Testing:** Use a tool like curl or Postman to hit the API endpoint, monitor the Step Functions execution, check DynamoDB status updates, and verify the final markdown and images in the S3 bucket.
    
**Phase 4: Production Readiness & Enhancements (Week 7)**
1.  **Logging & Monitoring:**
    -   Implement structured logging (JSON) in all Lambda functions.
    -   Set up CloudWatch Log Groups and Alarms for Lambda errors, high durations, Step Function execution failures.
    -   Create a basic CloudWatch Dashboard.
2.  **Security Hardening:**
    -   Review all IAM role permissions for least privilege.
    -   Ensure API Keys/Secrets are securely managed in Secrets Manager and accessed correctly.
    -   Validate all inputs rigorously.
3.  **Cost Optimization Review:**
    -   Check Lambda memory settings.
    -   Evaluate LLM/Image model choices (cost vs. quality trade-off).
    -   Set S3 lifecycle policies if needed.
4.  **Configuration Management:** Ensure all environment-specific settings (model names, timeouts, etc.) are configurable via environment variables or Parameter Store/AppConfig, managed by IaC.
5.  **CI/CD Pipeline:**
    -   Set up a pipeline (GitHub Actions, AWS CodePipeline, etc.) to automatically lint, test, build (SAM/CDK), and deploy changes on commits to develop/main.
        
**Phase 5: Deployment & Maintenance (Ongoing)**
1.  **Deployment:** Deploy the finalized stack to staging/production environments using the CI/CD pipeline.
2.  **Documentation:** Finalize README, document API usage, operational procedures.
3.  **Monitoring:** Actively monitor logs, alarms, and costs.
4.  **Iteration:** Gather feedback, refine prompts, update models, add features based on usage.
5.  **Maintenance:** Keep dependencies (Python packages, Lambda runtimes) updated. Adapt to any AI API changes.
    
----------
**Key Challenges & Considerations:**
-   **Prompt Engineering:** Achieving consistent, high-quality output requires significant iteration on prompts for each agent.
-   **AI API Costs:** LLM and image generation calls can be expensive. Monitor usage closely.
-   **AI API Latency & Timeouts:** Some AI calls (especially research/long rewrites/image gen) can be slow. Ensure Lambda timeouts and Step Function task timeouts are adequate. Use asynchronous patterns correctly.
-   **Error Handling:** Robustly handle failures from AI APIs, network issues, data inconsistencies. Step Functions helps manage workflow-level errors.
-   **State Management:** Passing potentially large data (like full articles) directly between Lambdas is inefficient and hits limits. Rely on passing S3 URIs via Step Functions state.
-   **Testing Orchestration:** Testing the full Step Functions flow can be complex, often requiring deployment to a test environment.
-   **Idempotency:** Design functions to be safe to retry where possible.
    
This plan provides a comprehensive roadmap. Remember to be iterative – test each component thoroughly before integrating it into the larger workflow. Good luck!
