"""Response helpers for building standardized metadata"""
from typing import Any, Dict


def build_update_metadata(result: Dict[str, Any], **extra: Any) -> Dict[str, Any]:
    """
    Build standard metadata for update/append operations.
    
    Args:
        result: API response from Google Sheets
        **extra: Additional metadata fields to include
        
    Returns:
        Metadata dictionary with standard fields
    """
    updates = result.get("updates", {})
    metadata = {
        "updatedRange": updates.get("updatedRange"),
        "updatedRows": updates.get("updatedRows"),
        "updatedCells": updates.get("updatedCells"),
        "spreadsheetId": result.get("spreadsheetId"),
    }
    metadata.update(extra)
    return metadata


def build_read_metadata(result: Dict[str, Any], values: Any) -> Dict[str, Any]:
    """
    Build metadata for read operations.
    
    Args:
        result: API response from Google Sheets
        values: Values array from the response
        
    Returns:
        Metadata dictionary
    """
    return {
        "range": result.get("range"),
        "majorDimension": result.get("majorDimension"),
        "values_count": sum(len(r) for r in values) if isinstance(values, list) else 0,
    }


def build_delete_metadata(spreadsheet_id: str, sheet_id: int, sheet_label: str, 
                          row_start: int, row_end: int) -> Dict[str, Any]:
    """
    Build metadata for delete operations.
    
    Args:
        spreadsheet_id: Spreadsheet ID
        sheet_id: Sheet ID
        sheet_label: Sheet label/name
        row_start: Starting row (1-indexed)
        row_end: Ending row (1-indexed, inclusive)
        
    Returns:
        Metadata dictionary
    """
    return {
        "deletedRowsCount": (row_end - row_start + 1),
        "sheetId": sheet_id,
        "spreadsheetId": spreadsheet_id,
        "affectedRange": f"{sheet_label}!{row_start}:{row_end}"
    }

