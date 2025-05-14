from typing import Any, Dict


def create_homepage_card(base_url: str) -> Dict[str, Any]:
    """
    Creates the Card Service JSON for the add-on homepage.
    """
    card_json = {
        "action": {
            "navigations": [
                {
                    "pushCard": {
                        "header": {
                            "title": "Ads Text Generator",
                            "subtitle": "Welcome! Ready to generate some ads?",
                            "imageUrl": "https://www.gstatic.com/images/icons/material/system/1x/extension_white_24dp.png",
                            "imageType": "SQUARE"
                        },
                        "sections": [
                            {
                                "widgets": [
                                    {
                                        "textParagraph": {
                                            "text": "Select product rows in your sheet and click 'Generate Ads' below to get started."
                                        }
                                    },
                                    {
                                        "buttonList": {
                                            "buttons": [
                                                {
                                                    "text": "Generate Ads",
                                                    "onClick": {
                                                        "action": {
                                                            "function": f"{base_url}/gws/generateAdsForm",
                                                            "parameters": []
                                                        }
                                                    }
                                                },
                                                {
                                                    "text": "Settings",
                                                    "onClick": {
                                                        "action": {
                                                            "function": f"{base_url}/gws/settingsForm",
                                                            "parameters": []
                                                        }
                                                    }
                                                }
                                            ]
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
