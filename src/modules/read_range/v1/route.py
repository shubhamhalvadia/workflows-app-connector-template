from flask import request as flask_request
from workflows_cdk import Response, Request, ManagedError
from main import router
from src.utils.google_sheets import read_values, validate_a1_notation, DEFAULT_RANGE
from src.utils.common_content import get_sheets_content
from src.utils.auth_helper import get_token_from_request
from src.utils.validation_helpers import extract_sheet_label
from src.utils.response_helpers import build_read_metadata


@router.route("/content", methods=["POST"])
def content():
    """Fetch sheets for dynamic dropdown"""
    return get_sheets_content(Request(flask_request))


@router.route("/execute", methods=["POST"])
def execute():
    """Execute read range operation"""
    request = Request(flask_request)
    data = request.data

    spreadsheet_id = data.get("spreadsheet_id")
    range_a1 = data.get("range_a1")
    sheet = data.get("sheet")

    if not spreadsheet_id:
        raise ManagedError.validation_error("spreadsheet_id is required")

    # Build range from sheet or use provided range_a1
    if not range_a1:
        if sheet:
            sheet_label = extract_sheet_label(sheet)
            range_a1 = f"{sheet_label}!{DEFAULT_RANGE}"
        else:
            raise ManagedError.validation_error("Provide range_a1 or select a sheet")
    else:
        validate_a1_notation(range_a1)

    try:
        token = get_token_from_request(request)

        value_render_option = (data.get("value_render_option") or {}).get("id")
        date_time_render_option = (data.get("date_time_render_option") or {}).get("id")

        result = read_values(
            spreadsheet_id,
            range_a1,
            token,
            value_render_option=value_render_option,
            date_time_render_option=date_time_render_option,
        )

        values = result.get("values", [])
        metadata = build_read_metadata(result, values)
        
        return Response.success(data=values, metadata=metadata)
    except ManagedError as me:
        return Response.error(me, status_code=me.status_code)
    except Exception as e:
        return Response.error(ManagedError.service_error(str(e), service="google_sheets"))


