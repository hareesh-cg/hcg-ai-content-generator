import yaml
import re
from datetime import datetime

from utils.logger_config import get_logger
from utils import constants as Constants

logger = get_logger(__name__)

def execute(post_item: dict, website_settings: dict, event_data: dict) -> str:
    """Assembles the final Markdown file from refined text, images, and metadata."""

    logger.info("Starting Markdown assembly...")

    refined_content = event_data.get("refined_article_content")
    if not refined_content:
        raise ValueError("Missing 'refined_article_content' for Markdown agent.")

    metadata = post_item.get(Constants.METADATA, {})
    image_s3_uris = post_item.get(Constants.IMAGE_URIS, [])
    blog_title = post_item.get(Constants.BLOG_TITLE, "Untitled Article")
    # formatting_notes = website_settings.get(Constants.MARKDOWN_FORMATTING_NOTES, "") # Use if needed

    # --- 1. Prepare YAML Front Matter (Optional but common) ---
    front_matter = {}
    if metadata.get("metaTitle"): front_matter['title'] = metadata['metaTitle']
    if metadata.get("metaDescription"): front_matter['description'] = metadata['metaDescription']
    if metadata.get("keywords"): front_matter['keywords'] = metadata['keywords']
    # Add other relevant metadata from post_item or website_settings if desired
    front_matter['date'] = datetime.utcnow().isoformat() + "Z" 

    final_markdown = ""
    if front_matter:
        try:
            # Use safe_dump, disable aliases for cleaner output
            yaml_string = yaml.safe_dump(front_matter, default_flow_style=False, allow_unicode=True, sort_keys=False)
            final_markdown += f"---\n{yaml_string}---\n\n"
            logger.info("Generated YAML front matter.")
        except Exception as e:
            logger.warning(f"Could not generate YAML front matter: {e}")
            # Proceed without front matter if YAML fails

    # --- 2. Simple Image Placement Strategy ---
    # Split content into paragraphs (basic split on double newline)
    paragraphs = re.split(r'\n\s*\n', refined_content.strip())
    
    # Remove empty paragraphs that might result from splitting
    paragraphs = [p for p in paragraphs if p.strip()] 
    
    num_paragraphs = len(paragraphs)
    num_images = len(image_s3_uris)
    
    logger.info(f"Attempting to place {num_images} images into {num_paragraphs} paragraphs.")

    # Simple strategy: Insert an image roughly every N paragraphs
    # Avoid inserting right at the beginning or very end if possible
    if num_images > 0 and num_paragraphs > 1:
        insert_interval = max(1, (num_paragraphs - 1) // (num_images + 1)) # Calculate interval, ensure at least 1
        image_index = 0
        content_with_images = []
        for i, para in enumerate(paragraphs):
            content_with_images.append(para)
            # Insert after paragraph `i`, if interval met and images remain
            # Start inserting after the first paragraph (i > 0)
            if i > 0 and (i + 1) % insert_interval == 0 and image_index < num_images:
                img_uri = image_s3_uris[image_index]
                # Basic alt text - could be improved using slugs or metadata later
                alt_text = f"Image related to {blog_title} - {image_index + 1}"
                image_markdown = f"\n\n![{alt_text}]({img_uri})\n"
                content_with_images.append(image_markdown)
                logger.debug(f"Inserted image {image_index+1} after paragraph {i+1}")
                image_index += 1
        
        # If any images remain (e.g., very short article), append them at the end? Or discard?
        # For now, we just place based on interval.

        # Join paragraphs and images back together
        body_content = "\n\n".join(content_with_images)
    else:
        # No images or not enough paragraphs, just use original content
        body_content = refined_content

    final_markdown += body_content

    logger.info("Markdown assembly complete.")
    return final_markdown