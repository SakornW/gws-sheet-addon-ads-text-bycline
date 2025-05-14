import logging
from typing import Any, Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)

GOOGLE_SHEETS_API_BASE_URL = "https://sheets.googleapis.com/v4/spreadsheets"


async def get_sheet_values(
    token: str, spreadsheet_id: str, range_a1: str
) -> Optional[List[List[Any]]]:
    """
    Fetches values from a Google Sheet range using the Sheets API.
    """
    url = f"{GOOGLE_SHEETS_API_BASE_URL}/{spreadsheet_id}/values/{range_a1}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    logger.info(f"Fetching sheet values from URL: {url}")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                response.raise_for_status()  # Raises an exception for HTTP errors 4xx/5xx
                data = await response.json()
                logger.info(f"Successfully fetched sheet values for range {range_a1}. Values: {data.get('values')}")
                return data.get("values")
    except aiohttp.ClientError as e:
        logger.error(f"AIOHTTP client error fetching sheet values for range {range_a1}: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Unexpected error fetching sheet values for range {range_a1}: {e}", exc_info=True)
    return None


async def update_sheet_values(
    token: str, spreadsheet_id: str, range_a1: str, values: List[List[Any]]
) -> Optional[Dict[str, Any]]:
    """
    Updates values in a Google Sheet range using the Sheets API.
    """
    url = f"{GOOGLE_SHEETS_API_BASE_URL}/{spreadsheet_id}/values/{range_a1}?valueInputOption=USER_ENTERED"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    body = {
        "range": range_a1,
        "majorDimension": "ROWS",
        "values": values,
    }
    logger.info(f"Updating sheet values at URL: {url} with body: {body}")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.put(url, headers=headers, json=body) as response:
                response.raise_for_status()
                result = await response.json()
                logger.info(f"Successfully updated sheet values for range {range_a1}. Result: {result}")
                return result
    except aiohttp.ClientError as e:
        logger.error(f"AIOHTTP client error updating sheet values for range {range_a1}: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Unexpected error updating sheet values for range {range_a1}: {e}", exc_info=True)
    return None
