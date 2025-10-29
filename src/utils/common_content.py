"""Shared content handlers for dynamic form fields"""
from typing import Any
from workflows_cdk import Response, Request, ManagedError
from src.utils.google_sheets import get_access_token, list_sheets


def get_sheets_content(request: Request) -> Any:
    """
    Shared content handler for fetching sheets from a spreadsheet.
    Used by all modules that need dynamic sheet selection.
    """
    data = request.data
    form_data = data.get("form_data", {})

    spreadsheet_id = form_data.get("spreadsheet_id")
    if not spreadsheet_id:
        return Response.content([
            {"content_object_name": "sheets_by_spreadsheet", "data": []}
        ])

    try:
        credentials = request.credentials
        token = get_access_token(credentials)
        sheets = list_sheets(spreadsheet_id, token)
        values = [
            {"value": {"id": s["sheetId"], "label": s["title"]}, "label": s["title"]}
            for s in sheets
        ]
        return Response.content([
            {"content_object_name": "sheets_by_spreadsheet", "data": values}
        ])
    except ManagedError as me:
        return Response.error(me, status_code=me.status_code)
    except Exception as e:
        return Response.error(ManagedError.service_error(str(e), service="google_sheets"))

