import logging
from pathlib import Path
from typing import Dict, List

from google import genai  # New SDK import
from google.genai import types  # New SDK types import
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.db.models import Product

# Note: HarmCategory, HarmBlockThreshold, Tool, GenerateContentConfig, GoogleSearch are expected to be in google.genai.types
logger = logging.getLogger(__name__)

# Initialize the client as per the new SDK, passing the API key explicitly
client = genai.Client(api_key=settings.GEMINI_API_KEY)

PROMPT_DIR = Path(__file__).parent.parent / "prompts"


def load_prompt_template(template_name: str) -> str:
    try:
        with open(PROMPT_DIR / template_name, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"Prompt template '{template_name}' not found in {PROMPT_DIR}")
        return "Error: Prompt template not found."


# Safety settings for generation - adjust as needed
# Assuming HarmCategory and HarmBlockThreshold are correctly found in types
SAFETY_SETTINGS = {
    types.HarmCategory.HARM_CATEGORY_HARASSMENT: types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    types.HarmCategory.HARM_CATEGORY_HATE_SPEECH: types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
}


# Initialize the Google Search tool as per the new documentation
google_search_tool = types.Tool(google_search=types.GoogleSearch())


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
        if "Error: Prompt template not found." in prompt_template_str:
            logger.error("Ad generation failed: prompt template not found.")
            return "Error: Ad generation setup issue. Please contact support."

        prompt = prompt_template_str.format(
            platform=platform,
            tone=tone,
            max_length=max_length,
            product_name=product_info['name'],
            product_description=product_info['description'],
            product_specifications=product_info['specifications'],
            product_cta_link=product_info['cta_link']
        )

        # Using the new SDK's client.aio.models.generate_content for async
        # Using 'gemini-2.0-flash' as per the "Search grounding" example with the new SDK
        model_name_for_tools = 'gemini-2.0-flash'  # Or another model known to work well with tools in the new SDK

        logger.info(f"Generating ad for: {product.name} using model {model_name_for_tools} with grounding. Prompt (first 200): {prompt[:200]}")

        generation_config = types.GenerateContentConfig(
            tools=[google_search_tool],
            safety_settings=SAFETY_SETTINGS  # Pass safety settings here
            # response_modalities=["TEXT"]  # Optional, from grounding example
        )

        # The `contents` argument should be the prompt directly
        response = await client.aio.models.generate_content(
            model=f'models/{model_name_for_tools}',  # Model name often prefixed with 'models/'
            contents=prompt,  # Pass the prompt string directly
            generation_config=generation_config  # Pass the config object
        )

        ad_text = ""
        if response.parts:
            ad_text = "".join(part.text for part in response.parts if hasattr(part, 'text')).strip()
        elif hasattr(response, 'text') and response.text:
            ad_text = response.text.strip()
        else:
            logger.warning(f"Primary text extraction failed for {product.name}. Checking candidates. Response: {response}")
            if response.candidates and response.candidates[0].content.parts:
                ad_text = "".join(part.text for part in response.candidates[0].content.parts if hasattr(part, 'text')).strip()

        if not ad_text:
            logger.error(f"Failed to generate ad text for {product.name}. Response: {response}")
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                logger.error(f"Prompt blocked for {product.name}. Reason: {response.prompt_feedback.block_reason_message}")
                return f"Ad generation blocked due to: {response.prompt_feedback.block_reason_message}"
            # Check for finish_reason in candidates if available
            if response.candidates and response.candidates[0].finish_reason:
                finish_reason_str = types.FinishReason(response.candidates[0].finish_reason).name
                logger.error(f"Generation finished for {product.name} with reason: {finish_reason_str}")
                if response.candidates[0].finish_reason != types.FinishReason.STOP:  # Not a normal stop
                    return f"Ad generation failed for {product.name}. Reason: {finish_reason_str}"
            raise ValueError("Failed to generate ad text, response was empty or malformed.")

        logger.info(f"Generated ad for {product.name}: {ad_text}")

        if response.candidates and response.candidates[0].grounding_metadata:
            metadata = response.candidates[0].grounding_metadata
            if hasattr(metadata, 'web_search_queries') and metadata.web_search_queries:
                logger.info(f"Grounding web_search_queries for {product.name}: {metadata.web_search_queries}")
            elif hasattr(metadata, 'search_entry_point') and metadata.search_entry_point:
                rendered_query = getattr(metadata.search_entry_point, 'rendered_query', 'N/A')
                logger.info(f"Grounding search_entry_point query for {product.name}: {rendered_query}")

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
