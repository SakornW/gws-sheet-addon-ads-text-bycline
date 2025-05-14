import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


def create_generate_ads_card(base_url: str) -> Dict[str, Any]:
    """
    Creates the Card Service JSON for the 'Generate Ads Options' form.
    This form collects data range, header row, output column, and generation parameters.
    """
    logger.info(f"Creating generate_ads_card with base_url: {base_url}")

    card_json = {
        "action": {
            "navigations": [
                {
                    "pushCard": {
                        "header": {"title": "Configure Ad Generation"},
                        "sections": [
                            {
                                "header": "Data Selection",
                                "widgets": [
                                    {
                                        "textInput": {
                                            "name": "data_range",
                                            "label": "Data Rows Range (e.g., Sheet1!A2:D100)",
                                            "hintText": "Range of data to process, excluding headers."
                                        }
                                    },
                                    {
                                        "textInput": {
                                            "name": "header_row",
                                            "label": "Header Row Number (e.g., 1)",
                                            "hintText": "Row number containing column headers."
                                        }
                                    },
                                    {
                                        "textInput": {
                                            "name": "output_column",
                                            "label": "Output Starting Column Letter (e.g., E)",
                                            "hintText": "Ads & references will be written starting here."
                                        }
                                    }
                                ]
                            },
                            {
                                "header": "Generation Parameters",
                                "widgets": [
                                    {
                                        "textInput": {
                                            "name": "tone",
                                            "label": "Ad Tone",
                                            "value": "Professional"
                                        }
                                    },
                                    {
                                        "textInput": {
                                            "name": "max_length",
                                            "label": "Max Ad Length",
                                            "value": "150",
                                            "type": "NUMBER"
                                        }
                                    }
                                ]
                            },
                            {
                                "widgets": [
                                    {
                                        "buttonList": {
                                            "buttons": [{
                                                "text": "Generate & Write Ads",
                                                "onClick": {
                                                    "action": {
                                                        "function": f"{base_url}/gws/generateAndWriteAds",  # Target endpoint
                                                        "parameters": [],  # Form inputs are sent automatically
                                                        "loadIndicator": "SPINNER"
                                                    }
                                                }
                                            }]
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                }
            ]
        }
    }
    return card_json
