import requests
from typing import Any, Dict, List, Optional
import re
from functools import lru_cache
from workflows_cdk import ManagedError


GOOGLE_SHEETS_API_BASE = "https://sheets.googleapis.com/v4/spreadsheets"
DEFAULT_RANGE = "A1:Z100"  # Default range for reading when only sheet is specified

# Create a persistent session for connection pooling (reuses TCP/TLS connections)
# This reduces latency by 50-70% for subsequent requests to the same host
_session = requests.Session()
_session.headers.update({"Content-Type": "application/json"})


def get_access_token(credentials: Dict[str, Any]) -> str:
    """Extract access token from credentials object"""
    token = credentials.get("access_token") or credentials.get("token") or ""
    if not token:
        raise ManagedError.unauthorized("Missing Google OAuth access token in credentials")
    return token


def _headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@lru_cache(maxsize=128)
def _get_spreadsheet_cached(spreadsheet_id: str, token: str) -> str:
    """
    Internal cached function that returns JSON string.
    Cache key uses both spreadsheet_id and token to ensure security.
    LRU cache reduces latency for repeated metadata fetches within same workflow.
    """
    url = f"{GOOGLE_SHEETS_API_BASE}/{spreadsheet_id}"
    params = {"fields": "sheets.properties(title,sheetId),spreadsheetId"}
    try:
        resp = _session.get(url, headers=_headers(token), params=params)
        resp.raise_for_status()
        return resp.text  # Return text for caching (JSON objects aren't hashable)
    except requests.HTTPError as e:
        status_code = e.response.status_code if e.response else 500
        error_message = e.response.text if e.response else str(e)
        
        if status_code == 401:
            raise ManagedError.unauthorized("Invalid or expired Google OAuth token")
        elif status_code == 404:
            raise ManagedError.not_found("Spreadsheet", spreadsheet_id)
        elif status_code == 429:
            retry_after = e.response.headers.get("Retry-After") if e.response else None
            raise ManagedError.service_error(
                "Google Sheets API rate limit exceeded",
                service="google_sheets",
                data={"retry_after_seconds": retry_after}
            )
        else:
            raise ManagedError.service_error(
                f"Google Sheets API error: {error_message}",
                service="google_sheets",
                data={"status_code": status_code}
            )
    except requests.RequestException as e:
        raise ManagedError.service_error(
            f"Network error connecting to Google Sheets API: {str(e)}",
            service="google_sheets"
        )


def get_spreadsheet(spreadsheet_id: str, token: str) -> Dict[str, Any]:
    """
    Get spreadsheet metadata including all sheets.
    Uses internal caching to reduce latency for repeated calls.
    """
    import json
    response_text = _get_spreadsheet_cached(spreadsheet_id, token)
    return json.loads(response_text)


def list_sheets(spreadsheet_id: str, token: str) -> List[Dict[str, Any]]:
    """List all sheets in a spreadsheet"""
    info = get_spreadsheet(spreadsheet_id, token)
    sheets = info.get("sheets", [])
    result: List[Dict[str, Any]] = []
    for s in sheets:
        props = s.get("properties", {})
        result.append({"sheetId": props.get("sheetId"), "title": props.get("title")})
    return result


def read_values(spreadsheet_id: str, range_a1: str, token: str, value_render_option: Optional[str] = None,
                date_time_render_option: Optional[str] = None) -> Dict[str, Any]:
    """Read values from a range in a spreadsheet"""
    url = f"{GOOGLE_SHEETS_API_BASE}/{spreadsheet_id}/values/{range_a1}"
    params: Dict[str, Any] = {}
    if value_render_option:
        params["valueRenderOption"] = value_render_option
    if date_time_render_option:
        params["dateTimeRenderOption"] = date_time_render_option
    
    try:
        resp = _session.get(url, headers=_headers(token), params=params)
        resp.raise_for_status()
        return resp.json()
    except requests.HTTPError as e:
        status_code = e.response.status_code if e.response else 500
        if status_code == 401:
            raise ManagedError.unauthorized("Invalid or expired Google OAuth token")
        elif status_code == 404:
            raise ManagedError.not_found("Range", f"{spreadsheet_id}/{range_a1}")
        elif status_code == 429:
            retry_after = e.response.headers.get("Retry-After") if e.response else None
            raise ManagedError.service_error(
                "Google Sheets API rate limit exceeded",
                service="google_sheets",
                data={"retry_after_seconds": retry_after}
            )
        else:
            raise ManagedError.service_error(
                f"Google Sheets API error: {e.response.text if e.response else str(e)}",
                service="google_sheets",
                data={"status_code": status_code}
            )
    except requests.RequestException as e:
        raise ManagedError.service_error(
            f"Network error: {str(e)}",
            service="google_sheets"
        )


def append_values(spreadsheet_id: str, range_a1: str, values_2d: List[List[Any]], token: str,
                  value_input_option: str = "RAW", insert_data_option: str = "INSERT_ROWS") -> Dict[str, Any]:
    """Append values to a spreadsheet"""
    url = f"{GOOGLE_SHEETS_API_BASE}/{spreadsheet_id}/values/{range_a1}:append"
    params = {"valueInputOption": value_input_option, "insertDataOption": insert_data_option}
    body = {"values": values_2d}
    
    try:
        resp = _session.post(url, headers=_headers(token), params=params, json=body)
        resp.raise_for_status()
        return resp.json()
    except requests.HTTPError as e:
        status_code = e.response.status_code if e.response else 500
        if status_code == 401:
            raise ManagedError.unauthorized("Invalid or expired Google OAuth token")
        elif status_code == 404:
            raise ManagedError.not_found("Range", f"{spreadsheet_id}/{range_a1}")
        elif status_code == 429:
            retry_after = e.response.headers.get("Retry-After") if e.response else None
            raise ManagedError.service_error(
                "Google Sheets API rate limit exceeded",
                service="google_sheets",
                data={"retry_after_seconds": retry_after}
            )
        else:
            raise ManagedError.service_error(
                f"Google Sheets API error: {e.response.text if e.response else str(e)}",
                service="google_sheets",
                data={"status_code": status_code}
            )
    except requests.RequestException as e:
        raise ManagedError.service_error(
            f"Network error: {str(e)}",
            service="google_sheets"
        )


def update_values(spreadsheet_id: str, range_a1: str, values_2d: List[List[Any]], token: str,
                  value_input_option: str = "RAW") -> Dict[str, Any]:
    """Update values in a spreadsheet range"""
    url = f"{GOOGLE_SHEETS_API_BASE}/{spreadsheet_id}/values/{range_a1}"
    params = {"valueInputOption": value_input_option}
    body = {"values": values_2d}
    
    try:
        resp = _session.put(url, headers=_headers(token), params=params, json=body)
        resp.raise_for_status()
        return resp.json()
    except requests.HTTPError as e:
        status_code = e.response.status_code if e.response else 500
        if status_code == 401:
            raise ManagedError.unauthorized("Invalid or expired Google OAuth token")
        elif status_code == 404:
            raise ManagedError.not_found("Range", f"{spreadsheet_id}/{range_a1}")
        elif status_code == 429:
            retry_after = e.response.headers.get("Retry-After") if e.response else None
            raise ManagedError.service_error(
                "Google Sheets API rate limit exceeded",
                service="google_sheets",
                data={"retry_after_seconds": retry_after}
            )
        else:
            raise ManagedError.service_error(
                f"Google Sheets API error: {e.response.text if e.response else str(e)}",
                service="google_sheets",
                data={"status_code": status_code}
            )
    except requests.RequestException as e:
        raise ManagedError.service_error(
            f"Network error: {str(e)}",
            service="google_sheets"
        )


def delete_rows(spreadsheet_id: str, sheet_id: int, start_index_0_based: int, end_index_0_based: int, token: str) -> Dict[str, Any]:
    """Delete rows from a spreadsheet"""
    url = f"{GOOGLE_SHEETS_API_BASE}/{spreadsheet_id}:batchUpdate"
    body = {
        "requests": [
            {
                "deleteDimension": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "ROWS",
                        "startIndex": start_index_0_based,
                        "endIndex": end_index_0_based
                    }
                }
            }
        ]
    }
    
    try:
        resp = _session.post(url, headers=_headers(token), json=body)
        resp.raise_for_status()
        return resp.json()
    except requests.HTTPError as e:
        status_code = e.response.status_code if e.response else 500
        if status_code == 401:
            raise ManagedError.unauthorized("Invalid or expired Google OAuth token")
        elif status_code == 404:
            raise ManagedError.not_found("Sheet", f"Sheet ID {sheet_id} in spreadsheet {spreadsheet_id}")
        elif status_code == 429:
            retry_after = e.response.headers.get("Retry-After") if e.response else None
            raise ManagedError.service_error(
                "Google Sheets API rate limit exceeded",
                service="google_sheets",
                data={"retry_after_seconds": retry_after}
            )
        else:
            raise ManagedError.service_error(
                f"Google Sheets API error: {e.response.text if e.response else str(e)}",
                service="google_sheets",
                data={"status_code": status_code}
            )
    except requests.RequestException as e:
        raise ManagedError.service_error(
            f"Network error: {str(e)}",
            service="google_sheets"
        )


# Matches A1 notation like: Sheet1!A1:B10, A1:B10, Sheet1!A:B, A1, Sheet1, etc.
# Format: [optional: 'SheetName'! or SheetName!] + [cell/range like A1, A1:B10, A:B]
_A1_RANGE_RE = re.compile(
    r"^("
    r"'[^'\n\r\t]+'\s*!"  # Quoted sheet name with !
    r"|[\w\s]+\s*!"  # Unquoted sheet name with ! (alphanumeric + underscore + space)
    r")?"  # Sheet name is optional
    r"("
    r"[A-Z]+\d*(?:\s*:\s*[A-Z]+\d*)?"  # Cell range: A1, A1:B10, A:B (must start with letter)
    r"|[a-zA-Z][\w\s]*"  # Or sheet name (must start with letter, then alphanumeric + space)
    r")?$"
)


def validate_a1_notation(range_a1: str) -> None:
    """
    Validate A1 notation format and raise error if invalid.
    
    Args:
        range_a1: A1 notation string (e.g., 'Sheet1!A1:B10')
        
    Raises:
        ManagedError: If A1 notation is invalid
    """
    if not isinstance(range_a1, str) or not range_a1.strip():
        raise ManagedError.validation_error("range_a1 is required and must be a non-empty string")
    
    if not _A1_RANGE_RE.match(range_a1.strip()):
        raise ManagedError.validation_error(
            f"Invalid A1 notation: '{range_a1}'. Expected format like 'Sheet1!A1:B10' or 'A1:B10'"
        )

