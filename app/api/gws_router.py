import logging  # Import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Request
from google.auth.transport import requests as google_auth_requests
from google.oauth2 import id_token
from sqlalchemy.orm import Session

from app.core.config import settings  # Import settings for GCP_OAUTH_CLIENT_ID
from app.db.crud import create_product  # To save products before generation
from app.db.models import Product  # For creating Product instances
from app.db.session import get_db
from app.services.ai_service import \
    generate_batch_ads_with_search  # The actual AI service

logger = logging.getLogger(__name__)  # Add logger

# We'll need to define Pydantic models for Card Service structures or use dicts
# from app.core.gws_cards import create_homepage_card, create_settings_card, create_generate_ads_card  # Example

router = APIRouter(prefix="/gws", tags=["Google Workspace"])


# Placeholder for verifying requests from Google Workspace
# This is crucial for security. Google sends an ID token.
# See: https://developers.google.com/workspace/add-ons/guides/alternate-runtimes#validating_requests
async def verify_google_id_token(request: Request) -> Dict[str, Any]:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized: Missing or invalid Authorization header")

    token = auth_header.split("Bearer ")[1]

    if not settings.GCP_OAUTH_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Server configuration error: GCP_OAUTH_CLIENT_ID not set.")

    try:
        id_info = id_token.verify_oauth2_token(
            token,
            google_auth_requests.Request(),
            settings.GCP_OAUTH_CLIENT_ID
        )

        # Verify issuer
        if id_info['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError('Wrong issuer.')

        # The audience should be your GCP OAuth Client ID
        if id_info['aud'] != settings.GCP_OAUTH_CLIENT_ID:
            raise ValueError('Token audience does not match client ID.')

        # You can now trust id_info.
        # Example: return user email or other relevant info
        return {"email": id_info.get("email"), "user_id": id_info.get("sub"), "id_info": id_info}

    except ValueError as e:
        # Invalid token
        raise HTTPException(status_code=401, detail=f"Unauthorized: Invalid token - {e}")
    except Exception as e:
        # Other errors
        raise HTTPException(status_code=500, detail=f"Token verification error: {e}")


@router.post("/homepage")
async def on_homepage(
    request_body: Dict[Any, Any],  # Google sends a specific JSON payload
    gws_user: Dict = Depends(verify_google_id_token),  # Enable once token verification is implemented
    db: Session = Depends(get_db)
):
    """
    Handles the homepageTrigger from the Google Workspace Add-on manifest.
    Returns a Card Service JSON to render the add-on homepage.
    """
    # request_body contains information like hostApp, platform, userLocale, etc.
    # user_email = gws_user.get("email")  # If token verification provides it

    # For now, return a simple card structure.
    # This should be built using a helper function or a Card Builder utility.
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
                                                            "function": "https://<YOUR_BACKEND_URL>/gws/generateAdsForm",
                                                            "parameters": []  # Can add parameters if needed
                                                        }
                                                    }
                                                },
                                                {
                                                    "text": "Settings",
                                                    "onClick": {
                                                        "action": {
                                                            "function": "https://<YOUR_BACKEND_URL>/gws/settingsForm",
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


@router.post("/onFileScopeGranted")
async def on_file_scope_granted(
    request_body: Dict[Any, Any],
    gws_user: Dict = Depends(verify_google_id_token),
    db: Session = Depends(get_db)
):
    """
    Handles the onFileScopeGrantedTrigger. Typically, this can just render the homepage.
    """
    return await on_homepage(request_body, gws_user, db)  # Pass gws_user and db


# Placeholder for the endpoint that shows the ad generation form/card
@router.post("/generateAdsForm")
async def on_generate_ads_form(
    request_body: Dict[Any, Any],
    gws_user: Dict = Depends(verify_google_id_token),
    db: Session = Depends(get_db)
):
    # This endpoint would return a card with input fields for tone, length, etc.
    # and a button that calls the actual /api/v1/generate/sheet endpoint.
    # The selected sheet data needs to be passed from the client-side (Google Sheets)
    # to this endpoint, or this endpoint needs to instruct the client to gather it.
    # This part is more complex with alternate runtimes as direct sheet interaction is limited.
    # Google's example for alternate runtimes often involves client-side JS to make API calls.
    # However, for pure Card Service, the action would submit form inputs.

    # For now, a simple card:
    card_json = {
        "action": {
            "navigations": [
                {
                    "pushCard": {
                        "header": {"title": "Generate Ads Options"},
                        "sections": [
                            {
                                "widgets": [
                                    {"textInput": {"name": "tone", "label": "Ad Tone", "value": "Professional"}},
                                    {"textInput": {"name": "max_length", "label": "Max Length", "value": "150", "type": "NUMBER"}},
                                    {
                                        "buttonList": {
                                            "buttons": [{
                                                "text": "Generate",
                                                "onClick": {
                                                    "action": {
                                                        # This function would be the one that calls our /api/v1/generate/sheet
                                                        # It needs to gather selected sheet data and form inputs.
                                                        # This is where the complexity of client-server interaction for alternate runtimes comes in.
                                                        # For now, let's assume it's a placeholder for a more complex interaction
                                                        # or a direct call if we can pass sheet data.
                                                        "function": "https://<YOUR_BACKEND_URL>/gws/executeGenerateAds",
                                                        "parameters": [
                                                            {"key": "source", "value": "form"}
                                                            # We need a way to get selected range data here.
                                                            # This might involve a client-side call from a previous card
                                                            # or a more complex card interaction.
                                                        ],
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


@router.post("/settingsForm")
async def on_settings_form(
    request_body: Dict[Any, Any],
    gws_user: Dict = Depends(verify_google_id_token),
    db: Session = Depends(get_db)
):
    # This would return a card for settings, similar to the Apps Script version.
    # For now, a placeholder.
    card_json = {
        "action": {
            "navigations": [
                {
                    "pushCard": {
                        "header": {"title": "Settings (Placeholder)"},
                        "sections": [{"widgets": [{"textParagraph": {"text": "Settings will be configured here."}}]}]
                    }
                }
            ]
        }
    }
    return card_json


# This is the endpoint that would actually call your existing /api/v1/generate/sheet
# It needs to receive data from the form submitted by /gws/generateAdsForm
@router.post("/executeGenerateAds")
async def on_execute_generate_ads(
    request_body: Dict[Any, Any],  # This will contain formInputs
    gws_user: Dict = Depends(verify_google_id_token),
    db: Session = Depends(get_db)
):
    logger.info(f"on_execute_generate_ads called with request_body: {request_body}")  # Log the request body

    # Extract form inputs
    form_inputs = request_body.get("commonEventObject", {}).get("formInputs", {})
    tone = form_inputs.get("tone", {}).get("stringInputs", {}).get("value", ["Professional"])[0]
    max_length_str = form_inputs.get("max_length", {}).get("stringInputs", {}).get("value", ["150"])[0]
    max_length = int(max_length_str) if max_length_str.isdigit() else 150

    # HOW TO GET SHEET DATA?
    # This is the tricky part with alternate runtimes and pure Card Service.
    # The manifest doesn't directly give us the selected range.
    # Option 1: Client-side call from Sheets (not pure alternate runtime for this action)
    # Option 2: The add-on framework might pass some context if the action was triggered from a specific selection.
    #           We need to inspect `request_body` for `sheets.selected Zellen` or similar.
    # Option 3: A multi-step card process:
    #           a. Card 1: Button "Prepare Data" -> calls an endpoint.
    #           b. Endpoint 1: Returns a card that instructs user or uses Sheets API (if authorized) to get data.
    #           c. Card 2: Shows data, user confirms -> calls /executeGenerateAds with data.

    # For now, let's assume sheet_data is somehow passed or we use a placeholder.
    # This needs to be resolved based on how Google Workspace Add-on framework handles data passing for HTTP endpoints.
    # The `hostApp` and `platform` from `request_body.commonEventObject` can be useful.
    # It might be in `request_body.sheets.selected Zellen` or similar, need to check Google's payload structure.

    placeholder_sheet_data = [
        {"Product Name": "Test Product 1", "Product Description": "A great test product."},
        {"Product Name": "Test Product 2", "Product Description": "Another fantastic item."}
    ]

    # Call your existing internal API endpoint (or its logic directly)
    # This assumes your /api/v1/generate/sheet is accessible internally or you refactor its logic.
    # For simplicity, let's imagine calling a helper that encapsulates that logic.

    # from app.api.endpoints import generate_ads_from_sheet  # This would create a circular dependency if not careful
    # For now, let's mock the call to the actual generation logic
    # --- START REPLACEMENT OF MOCK LOGIC ---
    user_id = gws_user.get("user_id")  # Assuming verify_google_id_token returns this
    if not user_id:
        # Fallback or raise error if user_id is not available
        # This depends on how you want to handle user association
        # For now, let's use a placeholder if not found, though this isn't ideal for production
        user_id = 1  # Placeholder, ensure this aligns with your user management

    db_products: List[Product] = []
    product_names_map = {}  # To map product ID back to name for response

    for item_data in placeholder_sheet_data:
        # Create Product in DB
        # This assumes placeholder_sheet_data items have 'Product Name', 'Product Description', etc.
        db_product = create_product(
            db=db,
            user_id=user_id,  # Associate with the authenticated GWS user
            name=item_data.get("Product Name", "Unknown Product"),
            description=item_data.get("Product Description"),
            specifications=item_data.get("Specifications"),
            cta_link=item_data.get("CTA Link")
        )
        db_products.append(db_product)
        product_names_map[db_product.id] = db_product.name

    generated_ads_map: Dict[int, str] = {}
    if db_products:
        generated_ads_map = await generate_batch_ads_with_search(
            products=db_products,
            tone=tone,
            max_length=max_length,
            platform="Facebook"  # Assuming platform is fixed for now or comes from params
        )

    generated_ads_payload = []
    for product_id, ad_text in generated_ads_map.items():
        generated_ads_payload.append({
            "product_name": product_names_map.get(product_id, "Unknown Product"),
            "ad_text": ad_text,
            "platform": "Facebook"
        })
    # --- END REPLACEMENT OF MOCK LOGIC ---

    # Return a card displaying the results
    sections = []
    for ad in generated_ads_payload:
        sections.append({
            "widgets": [
                {"textParagraph": {"text": f"<b>{ad['product_name']}</b>"}},
                {"textParagraph": {"text": ad['ad_text']}}
            ]
        })

    card_json = {
        "action": {
            "navigations": [
                {
                    "pushCard": {
                        "header": {"title": "Generated Ads"},
                        "sections": sections
                    }
                }
            ]
        }
    }
    return card_json
