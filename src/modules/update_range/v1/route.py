from flask import request as flask_request
from workflows_cdk import Response, Request, ManagedError
from main import router
from src.utils.google_sheets import update_values, validate_a1_notation
from src.utils.auth_helper import get_token_from_request
from src.utils.validation_helpers import extract_object_id
from workflows_cdk.core.validation import validate_array


@router.route("/execute", methods=["POST"])
def execute():
    """Execute update range operation"""
    request = Request(flask_request)
    data = request.data
    
    spreadsheet_id = data.get("spreadsheet_id")
    if not spreadsheet_id:
        raise ManagedError.validation_error("spreadsheet_id is required")
    
    range_a1 = data.get("range_a1")
    if not range_a1 or not isinstance(range_a1, str):
        raise ManagedError.validation_error("range_a1 is required and must be a string")
    
    validate_a1_notation(range_a1)
    
    values_data = data.get("values")
    if not values_data:
        raise ManagedError.validation_error("values is required")
    
    try:
        values = validate_array(values_data, "values")
        if not isinstance(values, list) or len(values) == 0:
            raise ManagedError.validation_error("values must be a non-empty array")
        
        for i, row in enumerate(values):
            if not isinstance(row, list):
                raise ManagedError.validation_error(f"Row {i+1} must be an array")
    
    except ValueError as e:
        raise ManagedError.validation_error(str(e))
    
    try:
        token = get_token_from_request(request)
        
        value_input_option = extract_object_id(data.get("value_input_option"), "value_input_option") or "USER_ENTERED"
        
        result = update_values(
            spreadsheet_id,
            range_a1,
            values,
            token,
            value_input_option=value_input_option
        )
        
        metadata = {
            "updatedRange": result.get("updatedRange"),
            "updatedRows": result.get("updatedRows"),
            "updatedCells": result.get("updatedCells"),
            "updatedColumns": result.get("updatedColumns"),
            "spreadsheetId": result.get("spreadsheetId")
        }
        
        return Response.success(data=result, metadata=metadata)
    except ManagedError:
        raise
    except Exception as e:
        return Response.error(ManagedError.service_error(str(e), service="google_sheets"))

