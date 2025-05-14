import logging
import re
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def get_sheet_name_and_columns_from_range(a1_notation: str) -> Optional[Tuple[str, str, str]]:
    """
    Parses A1 notation (e.g., 'Sheet1!A2:D100' or 'A2:D100') to extract
    sheet name (if present), start column, and end column.
    Returns a tuple (sheet_name, start_col, end_col) or None if parsing fails.
    Sheet name defaults to 'Sheet1' if not specified and there's no '!'
    but for add-ons, it's better if the sheet name is explicit if not the first sheet.
    If no '!' is present, it assumes the range is for the first/active sheet and sheet_name will be None.
    """
    if not a1_notation:
        return None

    # Regex to capture: optional sheet name, start column, start row, end column, end row
    # This version is more flexible for ranges like 'A2:D' or 'A:D' or 'A2:D100'
    match = re.match(r"^(?:'?([^'!]+)'?!)?([A-Z]+)(\d+)?:([A-Z]+)(\d+)?$", a1_notation, re.IGNORECASE)
    if match:
        sheet_name, start_col, _start_row, end_col, _end_row = match.groups()
        return sheet_name, start_col.upper(), end_col.upper()

    # Try matching ranges with only columns (e.g., 'Sheet1!A:D' or 'A:D')
    match_cols_only = re.match(r"^(?:'?([^'!]+)'?!)?([A-Z]+):([A-Z]+)$", a1_notation, re.IGNORECASE)
    if match_cols_only:
        sheet_name, start_col, end_col = match_cols_only.groups()
        return sheet_name, start_col.upper(), end_col.upper()

    logger.warning(f"Could not parse A1 notation for columns: {a1_notation}")
    return None


def get_sheet_name_and_start_row(a1_notation: str) -> Optional[Tuple[Optional[str], int]]:
    """
    Parses A1 notation to extract sheet name and starting row number.
    e.g., 'Sheet1!A2:D100' -> ('Sheet1', 2)
    e.g., 'A2:D100' -> (None, 2)
    """
    if not a1_notation:
        return None
    match = re.match(r"^(?:'?([^'!]+)'?!)?[A-Z]+(\d+):?[A-Z]*\d*$", a1_notation, re.IGNORECASE)
    if match:
        sheet_name, start_row_str = match.groups()
        try:
            return sheet_name, int(start_row_str)
        except ValueError:
            logger.warning(f"Could not parse start row from A1 notation: {a1_notation}")
            return None
    logger.warning(f"Could not parse A1 notation for start row: {a1_notation}")
    return None


def col_to_num(col_str: str) -> int:
    """Converts a column letter (A, B, ..., Z, AA, AB, ...) to a 0-indexed number."""
    num = 0
    for char in col_str:
        if 'A' <= char <= 'Z':
            num = num * 26 + (ord(char.upper()) - ord('A')) + 1
        else:
            raise ValueError(f"Invalid column character: {char}")
    return num - 1  # 0-indexed


def num_to_col(num: int) -> str:
    """Converts a 0-indexed number to a column letter (A, B, ..., Z, AA, AB, ...)."""
    if num < 0:
        raise ValueError("Column number cannot be negative.")
    col_str = ""
    num += 1  # 1-indexed for calculation
    while num > 0:
        num, remainder = divmod(num - 1, 26)
        col_str = chr(65 + remainder) + col_str
    return col_str


def construct_header_range(data_range_a1: str, header_row_number: int) -> Optional[str]:
    """
    Constructs the A1 notation for the header range based on the data range and header row number.
    Example: data_range_a1='Sheet1!A2:D100', header_row_number=1 -> 'Sheet1!A1:D1'
    """
    parsed_data_range = get_sheet_name_and_columns_from_range(data_range_a1)
    if not parsed_data_range:
        return None

    sheet_name, start_col, end_col = parsed_data_range

    header_range_str = f"{start_col}{header_row_number}:{end_col}{header_row_number}"
    if sheet_name:
        return f"'{sheet_name}'!{header_range_str}"
    return header_range_str
