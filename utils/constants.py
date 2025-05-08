"""A class to hold constant values used in the application."""

POST_ID = "postId" # Partition Key
WEBSITE_ID_REF = "websiteId"
BLOG_TITLE = "blogTitle"
POST_STATUS = "postStatus" # Status field
RESEARCH_ARTICLE_URI = "researchArticleUri"
REFINED_ARTICLE_URI = "refinedArticleUri"
IMAGE_PROMPTS = "imagePrompts"
IMAGE_URIS = "imageUris"
METADATA = "metadata"
MARKDOWN_URI = "markdownUri"
UPDATE_TIMESTAMP = "updateTimestamp"

# Website Settings Table Attributes
WEBSITE_ID = "websiteId" # Partition Key
WEBSITE_NAME = "websiteName"
WEBSITE_DESCRIPTION = "websiteDescription" 
BRAND_TONE = "brandTone" 
TARGET_AUDIENCE = "targetAudience"
ARTICLE_LENGTH_MIN = "articleLengthMin"
ARTICLE_LENGTH_MAX = "articleLengthMax"
IMAGE_STYLE_PROMPT = "imageStylePrompt"
IMAGE_ASPECT_RATIO = "imageAspectRatio"
NEGATIVE_IMAGE_PROMPTS = "negativeImagePrompts"
CORE_KEYWORDS = "coreKeywords"
NUM_IMAGE_PROMPTS = "numImagePrompts"

# S3 Key Prefixes / Names
S3_RESEARCH_FILENAME = "research_article.txt"
S3_REFINED_FILENAME = "refined_article.txt"
S3_MARKDOWN_FILENAME = "final_article.md"
S3_IMAGE_FOLDER = "images" # Subfolder for images within post path

# Status Prefixes (as defined in BaseService)
STATUS_PREFIX_RESEARCH = "RESEARCH"
STATUS_PREFIX_REFINE = "REFINE"
STATUS_PREFIX_IMAGE_PROMPT = "IMAGE_PROMPT"
STATUS_PREFIX_IMAGE_GEN = "IMAGE_GEN"

# Full Status Strings (Derived or explicit)
STATUS_STARTED_SUFFIX = "_STARTED"
STATUS_COMPLETE_SUFFIX = "_COMPLETE"
STATUS_FAILED_SUFFIX = "_FAILED"