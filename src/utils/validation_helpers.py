"""Validation helpers for common data extraction and validation patterns"""
from typing import Any, Dict
from workflows_cdk import ManagedError


def extract_sheet_label(sheet: Any) -> str:
    """
    Extract sheet label or ID from sheet object.
    
    Args:
        sheet: Sheet object from form data (should be dict with 'label' or 'id')
        
    Returns:
        Sheet label/title string
        
    Raises:
        ManagedError: If sheet is missing, invalid, or has no label/id
    """
    if not sheet or not isinstance(sheet, dict):
        raise ManagedError.validation_error("sheet is required and must be valid")
    
    label = sheet.get("label") or sheet.get("id")
    if not label:
        raise ManagedError.validation_error("sheet is invalid; missing label or id")
    
    return str(label)


def extract_object_id(obj: Any, field_name: str) -> str:
    """
    Extract 'id' field from SelectWidget object.
    
    Args:
        obj: Object from form data (dict with 'id' field)
        field_name: Name of the field for error messages
        
    Returns:
        ID string
        
    Raises:
        ManagedError: If object or ID is missing
    """
    if not obj or not isinstance(obj, dict):
        return ""
    
    obj_id = obj.get("id")
    if not obj_id:
        return ""
    
    return str(obj_id)

