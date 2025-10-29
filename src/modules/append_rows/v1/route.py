import json
from flask import request as flask_request
from workflows_cdk import Response, Request, ManagedError
from main import router
from src.utils.google_sheets import append_values
from src.utils.common_content import get_sheets_content
from src.utils.auth_helper import get_token_from_request
from src.utils.validation_helpers import extract_sheet_label, extract_object_id
from src.utils.response_helpers import build_update_metadata
from workflows_cdk.core.validation import validate_and_parse_json, validate_array


@router.route("/content", methods=["POST"])
def content():
    """Fetch sheets for dynamic dropdown"""
    return get_sheets_content(Request(flask_request))


@router.route("/execute", methods=["POST"])
def execute():
    """Execute append rows operation"""
    request = Request(flask_request)
    data = request.data
    
    spreadsheet_id = data.get("spreadsheet_id")
    if not spreadsheet_id:
        raise ManagedError.validation_error("spreadsheet_id is required")
    
    sheet_label = extract_sheet_label(data.get("sheet"))
    
    rows_data = data.get("rows")
    if not rows_data:
        raise ManagedError.validation_error("rows is required")
    
    try:
        rows = validate_array(rows_data, "rows")
        if not isinstance(rows, list) or len(rows) == 0:
            raise ManagedError.validation_error("rows must be a non-empty array")
        
        for i, row in enumerate(rows):
            if not isinstance(row, list):
                raise ManagedError.validation_error(f"Row {i+1} must be an array")
    
    except ValueError as e:
        raise ManagedError.validation_error(str(e))
    
    try:
        token = get_token_from_request(request)
        
        value_input_option = extract_object_id(data.get("value_input_option"), "value_input_option") or "USER_ENTERED"
        
        result = append_values(
            spreadsheet_id,
            sheet_label,
            rows,
            token,
            value_input_option=value_input_option,
            insert_data_option="INSERT_ROWS"
        )
        
        metadata = build_update_metadata(result, sheetId=data.get("sheet", {}).get("id"))
        
        return Response.success(data=result.get("updates", {}), metadata=metadata)
    except ManagedError:
        raise
    except Exception as e:
        return Response.error(ManagedError.service_error(str(e), service="google_sheets"))

