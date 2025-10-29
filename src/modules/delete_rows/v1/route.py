from flask import request as flask_request
from workflows_cdk import Response, Request, ManagedError
from main import router
from src.utils.google_sheets import delete_rows
from src.utils.common_content import get_sheets_content
from src.utils.auth_helper import get_token_from_request
from src.utils.validation_helpers import extract_sheet_label
from src.utils.response_helpers import build_delete_metadata


@router.route("/content", methods=["POST"])
def content():
    """Fetch sheets for dynamic dropdown"""
    return get_sheets_content(Request(flask_request))


@router.route("/execute", methods=["POST"])
def execute():
    """Execute delete rows operation"""
    request = Request(flask_request)
    data = request.data
    
    spreadsheet_id = data.get("spreadsheet_id")
    if not spreadsheet_id:
        raise ManagedError.validation_error("spreadsheet_id is required")
    
    sheet = data.get("sheet")
    sheet_label = extract_sheet_label(sheet)
    
    sheet_id = sheet.get("id")
    if not sheet_id:
        raise ManagedError.validation_error("sheet is invalid; missing id")
    
    try:
        sheet_id_int = int(sheet_id)
    except (ValueError, TypeError):
        raise ManagedError.validation_error(f"sheet id must be a number, got: {sheet_id}")
    
    row_start = data.get("row_start")
    if not row_start:
        raise ManagedError.validation_error("row_start is required")
    
    try:
        row_start_int = int(row_start)
        if row_start_int < 1:
            raise ManagedError.validation_error("row_start must be >= 1")
    except (ValueError, TypeError):
        raise ManagedError.validation_error("row_start must be a positive integer")
    
    row_end = data.get("row_end")
    if not row_end:
        raise ManagedError.validation_error("row_end is required")
    
    try:
        row_end_int = int(row_end)
        if row_end_int < 1:
            raise ManagedError.validation_error("row_end must be >= 1")
    except (ValueError, TypeError):
        raise ManagedError.validation_error("row_end must be a positive integer")
    
    if row_start_int > row_end_int:
        raise ManagedError.validation_error("row_start must be <= row_end")
    
    try:
        token = get_token_from_request(request)
        
        start_index_0_based = row_start_int - 1
        end_index_0_based = row_end_int
        
        result = delete_rows(
            spreadsheet_id,
            sheet_id_int,
            start_index_0_based,
            end_index_0_based,
            token
        )
        
        metadata = build_delete_metadata(
            spreadsheet_id,
            sheet_id_int,
            sheet_label,
            row_start_int,
            row_end_int
        )
        
        return Response.success(
            data={"spreadsheetId": spreadsheet_id, "updatedSpreadsheet": result.get("updatedSpreadsheet", {})},
            metadata=metadata
        )
    except ManagedError:
        raise
    except Exception as e:
        return Response.error(ManagedError.service_error(str(e), service="google_sheets"))

