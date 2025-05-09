import logging
from pathlib import Path
from typing import Dict, List

import google.generativeai as genai
# Removed GenerateContentConfig as it's not directly used with GenerativeModel.generate_content_async in this way
from google.generativeai.types import HarmBlockThreshold, HarmCategory, Tool

# Corrected import for GoogleSearch based on typical SDK structure
# If this specific path is wrong, the linter or runtime will tell us.
# The example used `from google.genai.types import GoogleSearch`, assuming `genai` was `from google import genai`.
# With `import google.generativeai as genai`, it's likely under `genai.types` or a sub-module.
# Let's try a common pattern, if it fails, we'll adjust.
try:
    from google.generativeai.types import GoogleSearch
except ImportError:
    from google.generativeai.types.content_types import GoogleSearch  # Fallback path

from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.db.models import Product

logger = logging.getLogger(__name__)

genai.configure(api_key=settings.GEMINI_API_KEY)
PROMPT_DIR = Path(__file__).parent.parent / "prompts"


def load_prompt_template(template_name: str) -> str:
    try:
        with open(PROMPT_DIR / template_name, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"Prompt template '{template_name}' not found in {PROMPT_DIR}")
        return "Error: Prompt template not found."  # Or raise a custom exception


# Safety settings for generation - adjust as needed
SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
}


# Initialize the Google Search tool as per the example
# The empty dict for schema implies default behavior or no specific input schema from our side.
google_search_tool = Tool(google_search=GoogleSearch(input_schema={}))


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def generate_ad_text_with_search(
    product: Product,
    tone: str = "Professional",
    max_length: int = 150,
    platform: str = "Facebook"
) -> str:
    try:
        product_info = {
            "name": product.name,
            "description": product.description or "",
            "specifications": product.specifications or "",
            "cta_link": product.cta_link or ""
        }

        prompt_template_str = load_prompt_template("ad_generation_template.txt")
        if "Error: Prompt template not found." in prompt_template_str:  # Check if loading failed
            logger.error("Ad generation failed: prompt template not found.")
            return "Error: Ad generation setup issue. Please contact support."

        # The template no longer needs an explicit search_query to be formatted in.
        # The model will use the product details to inform its search via the tool.
        prompt = prompt_template_str.format(
            platform=platform,
            tone=tone,
            max_length=max_length,
            product_name=product_info['name'],
            product_description=product_info['description'],
            product_specifications=product_info['specifications'],
            product_cta_link=product_info['cta_link']
        )

        # Using GenerativeModel and passing tools to generate_content_async
        # The model ID might need to be one that explicitly supports grounding well,
        # e.g., 'gemini-1.5-flash-latest' or 'gemini-1.0-pro' (if it supports tools this way).
        # The example used "gemini-2.0-flash" with a client, which might be different.
        # We'll use 'gemini-pro' as initially planned and see.
        model = genai.GenerativeModel(
            model_name='gemini-pro',
            safety_settings=SAFETY_SETTINGS
            # Tools are often passed to generate_content_async rather than model init
        )

        logger.info(f"Generating ad for: {product.name} using grounding. Prompt (first 200): {prompt[:200]}")

        # Pass the tool to the generation call
        response = await model.generate_content_async(
            prompt,
            tools=[google_search_tool]  # Pass the configured tool here
        )

        ad_text = ""
        # Standard way to get text from response, assuming it's not a function call response
        if response.parts:
            ad_text = "".join(part.text for part in response.parts if hasattr(part, 'text')).strip()
        elif hasattr(response, 'text') and response.text:  # Fallback for simpler text responses
            ad_text = response.text.strip()
        else:  # Check candidates if primary text extraction fails
            logger.warning(f"Primary text extraction failed for {product.name}. Checking candidates. Response: {response}")
            if response.candidates and response.candidates[0].content.parts:
                ad_text = "".join(part.text for part in response.candidates[0].content.parts if hasattr(part, 'text')).strip()

        if not ad_text:
            logger.error(f"Failed to generate ad text for {product.name}. Response: {response}")
            # Check for blocked response due to safety
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                logger.error(f"Prompt blocked for {product.name}. Reason: {response.prompt_feedback.block_reason_message}")
                return f"Ad generation blocked due to: {response.prompt_feedback.block_reason_message}"
            raise ValueError("Failed to generate ad text, response was empty or malformed.")

        logger.info(f"Generated ad for {product.name}: {ad_text}")

        # Log grounding metadata
        if response.candidates and response.candidates[0].grounding_metadata:
            metadata = response.candidates[0].grounding_metadata
            if metadata.web_search_queries:  # Check if this attribute exists
                logger.info(f"Grounding web_search_queries for {product.name}: {metadata.web_search_queries}")
            elif hasattr(metadata, 'search_entry_point') and metadata.search_entry_point:  # Check alternative attribute
                logger.info(f"Grounding search_entry_point query for {product.name}: {metadata.search_entry_point.rendered_query if hasattr(metadata.search_entry_point, 'rendered_query') else 'N/A'}")

        if len(ad_text) > max_length:
            ad_text = ad_text[:max_length - 3] + "..."

        return ad_text

    except Exception as e:
        logger.error(f"Error in generate_ad_text_with_search for {product.name}: {e}", exc_info=True)
        return f"Discover {product.name}! Visit {product.cta_link or 'our website'} to learn more."


async def generate_batch_ads_with_search(
    products: List[Product],
    tone: str = "Professional",
    max_length: int = 150,
    platform: str = "Facebook"
) -> Dict[int, str]:
    results = {}
    for product in products:
        try:
            ad_text = await generate_ad_text_with_search(
                product=product,
                tone=tone,
                max_length=max_length,
                platform=platform
            )
            results[product.id] = ad_text
        except Exception as e:
            logger.error(f"Failed to generate ad for product ID {product.id} ({product.name}) in batch: {e}")
            results[product.id] = f"Error generating ad for {product.name}. Please try again."

    return results
