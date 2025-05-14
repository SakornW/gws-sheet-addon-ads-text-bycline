import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple

from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings

logger = logging.getLogger(__name__)

client = genai.Client(api_key=settings.GEMINI_API_KEY)
PROMPT_DIR = Path(__file__).parent.parent / "prompts"


def load_prompt_template(template_name: str) -> str:
    try:
        with open(PROMPT_DIR / template_name, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"Prompt template '{template_name}' not found in {PROMPT_DIR}")
        return "Error: Prompt template not found."


SAFETY_SETTINGS = {
    types.HarmCategory.HARM_CATEGORY_HARASSMENT: types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    types.HarmCategory.HARM_CATEGORY_HATE_SPEECH: types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
}

google_search_tool = types.Tool(google_search=types.GoogleSearch())

AD_TEXT_FALLBACK = "Could not generate ad text. Please check product details or try again later."
REFERENCE_FALLBACK = "No reference strategy available."
RESPONSE_SEPARATOR = "---REFERENCE_STRATEGY_SEPARATOR---"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def generate_ad_text_with_search(
    product_row_data: Dict[str, str],  # Input is now just the row data
    tone: str = "Professional",
    max_length: int = 150,
    platform: str = "Facebook"
) -> Tuple[str, str]:
    # Try to find a product name for logging, otherwise use a generic placeholder
    product_name_for_log = product_row_data.get("Product Name", product_row_data.get("Name", "Unknown Product from Row"))

    try:
        product_data_dict_str = json.dumps(product_row_data, indent=2)

        prompt_template_str = load_prompt_template("ad_generation_template.txt")
        if "Error: Prompt template not found." in prompt_template_str:
            logger.error(f"Ad generation failed for {product_name_for_log}: prompt template not found.")
            return AD_TEXT_FALLBACK, REFERENCE_FALLBACK

        prompt = prompt_template_str.format(
            platform=platform,
            tone=tone,
            max_length=max_length,
            product_data_dict_str=product_data_dict_str
        )

        model_name_for_tools = 'gemini-1.5-flash-latest'  # Using a model known for tool use and good with grounding

        logger.info(f"Generating ad for: {product_name_for_log} using model {model_name_for_tools}. Prompt (first 300 chars): {prompt[:300]}")

        generation_config = types.GenerateContentConfig(
            tools=[google_search_tool],
            safety_settings=SAFETY_SETTINGS
        )

        response = await client.aio.models.generate_content(
            model=f'models/{model_name_for_tools}',
            contents=prompt,
            generation_config=generation_config
        )

        full_response_text = ""
        if response.parts:
            full_response_text = "".join(part.text for part in response.parts if hasattr(part, 'text')).strip()
        elif hasattr(response, 'text') and response.text:
            full_response_text = response.text.strip()
        else:
            logger.warning(f"Primary text extraction failed for {product_name_for_log}. Checking candidates. Response: {response}")
            if response.candidates and response.candidates[0].content.parts:
                full_response_text = "".join(part.text for part in response.candidates[0].content.parts if hasattr(part, 'text')).strip()

        if not full_response_text:
            logger.error(f"Failed to generate ad text for {product_name_for_log}. Response: {response}")
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                reason_msg = response.prompt_feedback.block_reason_message or "Safety block"
                logger.error(f"Prompt blocked for {product_name_for_log}. Reason: {reason_msg}")
                return f"Ad generation blocked: {reason_msg}", REFERENCE_FALLBACK
            if response.candidates and response.candidates[0].finish_reason:
                finish_reason_val = response.candidates[0].finish_reason
                finish_reason_str = types.FinishReason(finish_reason_val).name if isinstance(finish_reason_val, int) else str(finish_reason_val)
                logger.error(f"Generation finished for {product_name_for_log} with reason: {finish_reason_str}")
                if finish_reason_val != types.FinishReason.STOP:
                    return f"Ad generation failed: {finish_reason_str}", REFERENCE_FALLBACK
            return AD_TEXT_FALLBACK, REFERENCE_FALLBACK

        if RESPONSE_SEPARATOR in full_response_text:
            ad_text, reference_strategy = full_response_text.split(RESPONSE_SEPARATOR, 1)
            ad_text = ad_text.strip()
            reference_strategy = reference_strategy.strip()
        else:
            ad_text = full_response_text.strip()
            reference_strategy = REFERENCE_FALLBACK
            logger.warning(f"Response for {product_name_for_log} did not contain separator. Full response used as ad text.")

        logger.info(f"Generated ad for {product_name_for_log}: {ad_text}")
        logger.info(f"Reference/Strategy for {product_name_for_log}: {reference_strategy}")

        if response.candidates and hasattr(response.candidates[0], 'grounding_metadata') and response.candidates[0].grounding_metadata:
            metadata = response.candidates[0].grounding_metadata
            if hasattr(metadata, 'web_search_queries') and metadata.web_search_queries:
                logger.info(f"Grounding web_search_queries for {product_name_for_log}: {metadata.web_search_queries}")
            elif hasattr(metadata, 'search_entry_point') and metadata.search_entry_point:
                rendered_query = getattr(metadata.search_entry_point, 'rendered_query', 'N/A')
                logger.info(f"Grounding search_entry_point query for {product_name_for_log}: {rendered_query}")

        return ad_text, reference_strategy

    except Exception as e:
        logger.error(f"Error in generate_ad_text_with_search for {product_name_for_log}: {e}", exc_info=True)
        return AD_TEXT_FALLBACK, f"Error during generation: {str(e)}"


async def generate_batch_ads_with_search(
    products_data: List[Dict[str, str]],  # List of product row data dicts
    tone: str = "Professional",
    max_length: int = 150,
    platform: str = "Facebook"
) -> List[Tuple[str, str]]:  # Returns a list of (ad_text, reference_strategy) tuples
    results = []
    for product_row in products_data:
        try:
            # For logging within generate_ad_text_with_search, it will try to find a name.
            # No need to pass product_name_header_key anymore.
            ad_text, reference_strategy = await generate_ad_text_with_search(
                product_row_data=product_row,
                tone=tone,
                max_length=max_length,
                platform=platform
            )
            results.append((ad_text, reference_strategy))
        except Exception as e:
            # Attempt to get a product name for logging, if possible from the row data
            product_name_for_log_batch = product_row.get("Product Name", product_row.get("Name", "Unknown Product in Batch"))
            logger.error(f"Failed to generate ad for product '{product_name_for_log_batch}' in batch: {e}", exc_info=True)
            results.append((AD_TEXT_FALLBACK, f"Batch processing error: {str(e)}"))
    return results
