import pytest
from src.utils.google_sheets import validate_a1_notation
from workflows_cdk import ManagedError


def test_validate_a1_notation_valid_cases():
    """Valid A1 notation should not raise any errors"""
    # These should all pass without raising exceptions
    validate_a1_notation("Sheet1!A1:B10")
    validate_a1_notation("A1:B10")
    validate_a1_notation("Sheet Name!A1")
    validate_a1_notation("Sheet Name!A:B")
    validate_a1_notation("A1")
    validate_a1_notation("Sheet1")  # Entire sheet
    # If we get here, all validations passed
    assert True


def test_validate_a1_notation_invalid_cases():
    """Invalid A1 notation should raise ManagedError"""
    # Test each case individually to see which one fails
    try:
        validate_a1_notation("invalid-range")
        assert False, "Should have raised error for 'invalid-range'"
    except ManagedError:
        pass  # Expected
    
    try:
        validate_a1_notation("Sheet1!1A")
        assert False, "Should have raised error for 'Sheet1!1A'"
    except ManagedError:
        pass  # Expected
    
    try:
        validate_a1_notation("Sheet1!A1:1B")
        assert False, "Should have raised error for 'Sheet1!A1:1B'"
    except ManagedError:
        pass  # Expected
    
    try:
        validate_a1_notation("!A1")
        assert False, "Should have raised error for '!A1'"
    except ManagedError:
        pass  # Expected
    
    try:
        validate_a1_notation("Sheet1!A1:B10:C12")
        assert False, "Should have raised error for 'Sheet1!A1:B10:C12'"
    except ManagedError:
        pass  # Expected
    
    with pytest.raises(ManagedError, match="required and must be a non-empty string"):
        validate_a1_notation("")
    
    with pytest.raises(ManagedError, match="required and must be a non-empty string"):
        validate_a1_notation("   ")


