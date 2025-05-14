import logging  # Import logging
from typing import Any, Dict, List, Tuple

import requests
from fastapi import APIRouter, Depends, HTTPException, Request
from google.auth.transport import requests as google_auth_requests
from google.oauth2 import id_token
from sqlalchemy.orm import Session

from app.core.config import settings  # Import settings for GCP_OAUTH_CLIENT_ID
from app.core.gws_cards import generate_ads_card, homepage_card
from app.db.crud import create_product  # To save products before generation
from app.db.models import Product  # For creating Product instances
from app.db.session import get_db
from app.services.ai_service import \
    generate_batch_ads_with_search  # The actual AI service
from app.utils.google_api_clients import (  # Import sheets API client
    get_sheet_values, update_sheet_values)
from app.utils.sheets_utils import \
    construct_header_range  # Import the new utility

logger = logging.getLogger(__name__)  # Add logger

router = APIRouter(prefix="/gws", tags=["Google Workspace"])


# Placeholder for verifying requests from Google Workspace
# This is crucial for security. Google sends an ID token.
# See: https://developers.google.com/workspace/add-ons/guides/alternate-runtimes#validating_requests
async def verify_google_id_token(request: Request) -> Dict[str, Any]:
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        logger.warning(
            "verify_google_id_token: Missing or invalid Authorization header."
        )
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: Missing or invalid Authorization header",
        )

    token = auth_header.split("Bearer ")[1]
    logger.info(
        f"verify_google_id_token: All request headers: {dict(request.headers)}"
    )  # Log all headers
    # logger.info(token)  # Avoid logging the full token repeatedly if not necessary for this debug step

    # For SYSTEM_ID_TOKEN, the audience is the URL of the endpoint.
    # The GCP_OAUTH_CLIENT_ID is used for USER_ID_TOKEN.
    # We must also check SERVICE_ACCOUNT_EMAIL for SYSTEM_ID_TOKEN.

    if (
        not settings.SERVICE_ACCOUNT_EMAIL
    ):  # Check this first as it's critical for SYSTEM_ID_TOKEN
        logger.error(
            "verify_google_id_token: SERVICE_ACCOUNT_EMAIL is not set in settings."
        )
        raise HTTPException(
            status_code=500,
            detail="Server configuration error: SERVICE_ACCOUNT_EMAIL not set.",
        )

    # Construct the expected audience URL from the request
    x_forwarded_proto = request.headers.get("x-forwarded-proto")
    x_forwarded_host = request.headers.get("x-forwarded-host")
    scheme = x_forwarded_proto if x_forwarded_proto else request.url.scheme
    host = x_forwarded_host if x_forwarded_host else request.url.hostname

    # Reconstruct the URL with the determined scheme.
    # The audience in the token will be for the public-facing URL.
    # For Google Add-ons, this will always be HTTPS.
    expected_audience_url = f"{scheme}://{host}{request.url.path}"
    if request.url.query:  # Preserve query parameters if any
        expected_audience_url += f"?{request.url.query}"

    logger.info(
        f"verify_google_id_token: Verifying token against audience (URL): {expected_audience_url}"
    )

    try:
        id_info = id_token.verify_oauth2_token(
            token,
            google_auth_requests.Request(),
            audience=expected_audience_url,  # Verify against the endpoint URL for SYSTEM_ID_TOKEN
        )
        logger.info(
            f"verify_google_id_token: Token successfully verified against URL. Issuer: {id_info.get('iss')}, Audience: {id_info.get('aud')}, Email: {id_info.get('email')}"
        )

        # Verify issuer
        if id_info.get("iss") not in [
            "accounts.google.com",
            "https://accounts.google.com",
        ]:
            logger.error(
                f"verify_google_id_token: Invalid issuer: {id_info.get('iss')}"
            )
            raise ValueError("Wrong issuer.")

        # Verify the email claim in the token matches the add-on's service account email
        token_email = id_info.get("email")
        if not token_email:
            logger.error(
                "verify_google_id_token: Token does not contain an email claim."
            )
            raise ValueError("Token missing email claim.")

        if token_email.lower() != settings.SERVICE_ACCOUNT_EMAIL.lower():
            logger.error(
                f"verify_google_id_token: Token email '{token_email}' does not match configured SERVICE_ACCOUNT_EMAIL '{settings.SERVICE_ACCOUNT_EMAIL}'."
            )
            raise ValueError("Token email does not match service account.")

        return id_info

    except ValueError as e:
        logger.error(
            f"verify_google_id_token: ValueError during token verification: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=401, detail=f"Unauthorized: Invalid token - {e}"
        )
    except Exception as e:
        # Other errors
        raise HTTPException(status_code=500, detail=f"Token verification error: {e}")


@router.post("/homepage")
async def on_homepage(
    request_body: Dict[Any, Any],  # Google sends a specific JSON payload
    request: Request,  # To get the base URL for card actions
    jwt: Dict = Depends(
        verify_google_id_token
    ),  # Enable once token verification is implemented
    db: Session = Depends(get_db),
):
    """
    Handles the homepageTrigger from the Google Workspace Add-on manifest.
    Returns a Card Service JSON to render the add-on homepage.
    """

    logger.info(
        f"on_homepage called with request_body: {request_body}"
    )  # Log the request body
    if not request_body.get("sheets", {}):
        logger.warning("on_homepage: No sheets data in request body.")
        return {
            "hostAppAction": {"editorAction": {"requestFileScopeForActiveDocument": {}}}
        }

    # Construct the base URL from the incoming request, respecting x-forwarded-proto and x-forwarded-host
    x_forwarded_proto = request.headers.get("x-forwarded-proto")
    x_forwarded_host = request.headers.get("x-forwarded-host")
    scheme = x_forwarded_proto if x_forwarded_proto else request.url.scheme
    host = x_forwarded_host if x_forwarded_host else request.url.hostname
    base_url = f"{scheme}://{host}"
    logger.info(f"on_homepage: Constructed base_url for card actions: {base_url}")

    # get user email
    user_access_token = request_body.get("authorizationEventObject", {}).get(
        "userOAuthToken", {}
    )
    if user_access_token:
        url = "https://www.googleapis.com/oauth2/v3/userinfo"
        headers = {"Authorization": f"Bearer {user_access_token}"}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            user_info = response.json()
            logger.info(
                f"on_homepage: user_info.get('email'): {user_info.get('email')}"
            )
    return homepage_card.create_homepage_card(base_url)


@router.post("/onFileScopeGranted")
async def on_file_scope_granted(
    request_body: Dict[Any, Any],
    request: Request,  # To get the base URL for card actions
    gws_user: Dict = Depends(verify_google_id_token),
    db: Session = Depends(get_db),
):
    """
    Handles the onFileScopeGrantedTrigger. Typically, this can just render the homepage.
    """
    logger.info(f"on_file_scope_granted called with request_body: {request_body}")

    return await on_homepage(request_body, request, gws_user, db)  # Pass gws_user and db


# Placeholder for the endpoint that shows the ad generation form/card
@router.post("/generateAdsForm")
async def on_generate_ads_form(
    request_body: Dict[Any, Any],
    request: Request,
    gws_user: Dict = Depends(verify_google_id_token),
    db: Session = Depends(get_db),
):
    # This endpoint would return a card with input fields for tone, length, etc.
    # and a button that calls the actual /api/v1/generate/sheet endpoint.
    # The selected sheet data needs to be passed from the client-side (Google Sheets)
    # to this endpoint, or this endpoint needs to instruct the client to gather it.
    # This part is more complex with alternate runtimes as direct sheet interaction is limited.
    # Google's example for alternate runtimes often involves client-side JS to make API calls.
    # However, for pure Card Service, the action would submit form inputs.

    logger.info(f"on_generate_ads_form called with request_body: {request_body}")

    # Construct the base URL from the incoming request, respecting x-forwarded-proto and x-forwarded-host
    x_forwarded_proto = request.headers.get("x-forwarded-proto")
    x_forwarded_host = request.headers.get("x-forwarded-host")
    scheme = x_forwarded_proto if x_forwarded_proto else request.url.scheme
    host = x_forwarded_host if x_forwarded_host else request.url.hostname
    base_url = f"{scheme}://{host}"
    logger.info(
        f"on_generate_ads_form: Constructed base_url for card actions: {base_url}"
    )

    # For now, a simple card:
    card_json = generate_ads_card.create_generate_ads_card(base_url)
    return card_json


# This endpoint will process the form, read sheet data, call AI, and write back.
@router.post("/generateAndWriteAds")
async def generate_and_write_ads(
    request_body: Dict[Any, Any],  # This will contain formInputs from generate_ads_card
    request: Request,  # To potentially get userOAuthToken if not relying on gws_user from verify_google_id_token
    gws_user: Dict = Depends(verify_google_id_token),
    db: Session = Depends(get_db),
):
    logger.info(
        f"generate_and_write_ads called with request_body: {request_body}"
    )

    form_inputs = request_body.get("commonEventObject", {}).get("formInputs", {})
    if not form_inputs:
        logger.error("generate_and_write_ads: No formInputs found in request_body.")
        # Return a simple error card or notification
        return {
            "action": {
                "notification": {"text": "Error: Missing form data."}
            }
        }

    data_range = form_inputs.get("data_range", {}).get("stringInputs", {}).get("value", [None])[0]
    header_row_str = form_inputs.get("header_row", {}).get("stringInputs", {}).get("value", [None])[0]
    output_column = form_inputs.get("output_column", {}).get("stringInputs", {}).get("value", [None])[0]
    tone = form_inputs.get("tone", {}).get("stringInputs", {}).get("value", ["Professional"])[0]
    max_length_str = form_inputs.get("max_length", {}).get("stringInputs", {}).get("value", ["150"])[0]

    logger.info(f"generate_and_write_ads - Form Inputs: data_range='{data_range}', header_row='{header_row_str}', output_column='{output_column}', tone='{tone}', max_length='{max_length_str}'")

    if not all([data_range, header_row_str, output_column]):
        logger.error("generate_and_write_ads: Missing required form inputs (data_range, header_row, or output_column).")
        return {
            "action": {
                "notification": {"text": "Error: Missing required fields: Data Range, Header Row, or Output Column."}
            }
        }

    try:
        header_row = int(header_row_str)
        max_length = int(max_length_str)
    except ValueError:
        logger.error("generate_and_write_ads: Invalid number format for header_row or max_length.")
        return {
            "action": {
                "notification": {"text": "Error: Header Row and Max Length must be numbers."}
            }
        }

    # Placeholder for actual processing logic

    # 1. Get Sheet ID
    sheets_data = request_body.get("sheets", {})
    sheet_id = sheets_data.get("id")
    if not sheet_id:
        logger.error("generate_and_write_ads: Missing Sheet ID in request_body.sheets.id")
        return {"action": {"notification": {"text": "Error: Could not identify the Google Sheet."}}}
    logger.info(f"generate_and_write_ads: Sheet ID: {sheet_id}")

    # 2. Get userOAuthToken
    auth_event_object = request_body.get("authorizationEventObject", {})
    user_oauth_token = auth_event_object.get("userOAuthToken")
    if not user_oauth_token:
        logger.error("generate_and_write_ads: Missing userOAuthToken in authorizationEventObject.")
        return {"action": {"notification": {"text": "Error: Missing user authorization token."}}}
    logger.info(f"generate_and_write_ads: userOAuthToken (partial): {user_oauth_token[:20]}...")

    # 3. Construct Header Range
    header_a1_range = construct_header_range(data_range, header_row)
    if not header_a1_range:
        logger.error(f"generate_and_write_ads: Could not construct header range from data_range='{data_range}' and header_row='{header_row}'.")
        return {"action": {"notification": {"text": "Error: Invalid data range or header row format."}}}
    logger.info(f"generate_and_write_ads: Constructed header_a1_range: {header_a1_range}")

    # 4. Read Headers using Sheets API
    header_values = await get_sheet_values(
        token=user_oauth_token,
        spreadsheet_id=sheet_id,
        range_a1=header_a1_range
    )

    if not header_values or not header_values[0]:
        logger.error(f"generate_and_write_ads: Could not read header row from {header_a1_range} or header row is empty.")
        return {"action": {"notification": {"text": "Error: Could not read header row from sheet."}}}

    headers_list = [str(header) for header in header_values[0]]  # Ensure all headers are strings
    logger.info(f"generate_and_write_ads: Fetched headers: {headers_list}")

    # 5. Read Data Rows using Sheets API (from data_range)
    data_rows_values = await get_sheet_values(
        token=user_oauth_token,
        spreadsheet_id=sheet_id,
        range_a1=data_range  # Use the user-provided data_range
    )

    if not data_rows_values:
        logger.error(f"generate_and_write_ads: Could not read data rows from {data_range} or range is empty.")
        return {"action": {"notification": {"text": "Error: Could not read data rows from sheet."}}}

    logger.info(f"generate_and_write_ads: Fetched {len(data_rows_values)} data row(s). First row (sample): {data_rows_values[0] if data_rows_values else 'N/A'}")

    # 6. Prepare data for AI (list of dicts: {header: value})
    products_for_ai = []
    for row_values in data_rows_values:
        product_data = {}
        for i, header_name in enumerate(headers_list):
            if i < len(row_values):
                product_data[header_name] = str(row_values[i])  # Ensure value is string
            else:
                product_data[header_name] = ""  # Handle rows with fewer cells than headers
        products_for_ai.append(product_data)

    if not products_for_ai:
        logger.warning("generate_and_write_ads: No product data prepared for AI.")
        return {"action": {"notification": {"text": "No data to process after parsing."}}}

    logger.info(f"generate_and_write_ads: Prepared {len(products_for_ai)} products for AI. First product (sample): {products_for_ai[0] if products_for_ai else 'N/A'}")

    # 7. Call ai_service.generate_batch_ads_with_search
    # The AI service now expects a list of product data dictionaries.
    # It will return a list of (ad_text, reference_strategy) tuples, maintaining order.

    # We need to decide which header to use for logging within the AI service if a generic "Name" or "Product Name" isn't found.
    # For now, the AI service has a fallback. If a specific header is consistently used for product names,
    # we could pass that header name to `generate_batch_ads_with_search` if needed for its internal logging or result mapping,
    # but since we're using list indices now, it's not strictly necessary for result mapping.
    # The current `generate_batch_ads_with_search` doesn't require `product_name_header_key` anymore.

    ai_results: List[Tuple[str, str]] = await generate_batch_ads_with_search(
        products_data=products_for_ai,
        tone=tone,
        max_length=max_length,
        platform="Facebook"  # Assuming Facebook for now, can be a form input later
    )

    if not ai_results or len(ai_results) != len(products_for_ai):
        logger.error("generate_and_write_ads: AI service did not return expected results.")
        return {"action": {"notification": {"text": "Error: Failed to generate ads from AI service."}}}

    logger.info(f"generate_and_write_ads: Received {len(ai_results)} results from AI service.")
    # Example log of the first result, if any
    if ai_results:
        logger.info(f"generate_and_write_ads: First AI result - Ad: '{ai_results[0][0][:50]}...', Ref: '{ai_results[0][1][:50]}...'")

    # 8. Write results back to sheet using Sheets API
    ads_to_write = [[ad_text] for ad_text, _ in ai_results]  # Prepare data for writing (list of lists)

    # Determine the starting row from the data_range (e.g., "Sheet1!A2:D10" -> 2)
    # This is a simplified approach; a more robust parser might be needed for complex ranges.
    try:
        range_parts = data_range.split("!")[1].split(":")[0]  # e.g., "A2"
        start_row_for_output = int("".join(filter(str.isdigit, range_parts)))
    except (IndexError, ValueError) as e:
        logger.error(f"generate_and_write_ads: Could not parse start row from data_range '{data_range}': {e}")
        return {"action": {"notification": {"text": "Error: Could not determine output range."}}}

    # Construct the output range, e.g., "Sheet1!E2:E10" if output_column is E and data starts at row 2
    # Assuming output_column is a single letter like "E"
    # and ads_to_write has the same number of rows as products_for_ai
    output_range_a1 = f"{data_range.split('!')[0]}!{output_column}{start_row_for_output}:{output_column}{start_row_for_output + len(ads_to_write) - 1}"
    logger.info(f"generate_and_write_ads: Constructed output_range_a1 for writing: {output_range_a1}")

    update_result = await update_sheet_values(
        token=user_oauth_token,
        spreadsheet_id=sheet_id,
        range_a1=output_range_a1,
        values=ads_to_write
    )

    if update_result:
        logger.info(f"generate_and_write_ads: Successfully wrote {len(ads_to_write)} ads to sheet.")
        return {
            "action": {
                "notification": {"text": f"Successfully generated and wrote {len(ads_to_write)} ads to column {output_column}."}
            }
        }
    else:
        logger.error("generate_and_write_ads: Failed to write ads to sheet.")
        return {
            "action": {
                "notification": {"text": "Error: Ads generated but failed to write them to the sheet."}
            }
        }

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
        {
            "Product Name": "Test Product 1",
            "Product Description": "A great test product.",
        },
        {
            "Product Name": "Test Product 2",
            "Product Description": "Another fantastic item.",
        },
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
            cta_link=item_data.get("CTA Link"),
        )
        db_products.append(db_product)
        product_names_map[db_product.id] = db_product.name

    generated_ads_map: Dict[int, str] = {}
    if db_products:
        generated_ads_map = await generate_batch_ads_with_search(
            products=db_products,
            tone=tone,
            max_length=max_length,
            platform="Facebook",  # Assuming platform is fixed for now or comes from params
        )

    generated_ads_payload = []
    for product_id, ad_text in generated_ads_map.items():
        generated_ads_payload.append(
            {
                "product_name": product_names_map.get(product_id, "Unknown Product"),
                "ad_text": ad_text,
                "platform": "Facebook",
            }
        )
    # --- END REPLACEMENT OF MOCK LOGIC ---

    # Return a card displaying the results
    sections = []
    for ad in generated_ads_payload:
        sections.append(
            {
                "widgets": [
                    {"textParagraph": {"text": f"<b>{ad['product_name']}</b>"}},
                    {"textParagraph": {"text": ad["ad_text"]}},
                ]
            }
        )

    card_json = {
        "action": {
            "navigations": [
                {
                    "pushCard": {
                        "header": {"title": "Generated Ads"},
                        "sections": sections,
                    }
                }
            ]
        }
    }
    return card_json
