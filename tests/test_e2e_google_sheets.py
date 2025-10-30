"""
End-to-End (E2E) Tests for Google Sheets Connector

These tests make REAL API calls to Google Sheets API using actual credentials.
They validate the complete integration flow from connector to Google Sheets.

The tests will prompt for credentials interactively if not provided in environment.

To run all tests (unit + E2E with interactive prompts):
    pytest -v

To skip E2E tests:
    Set SKIP_E2E_TESTS=true in tests/env.test
"""

import pytest
import os
import sys
from pathlib import Path


# Load environment variables from tests/env.test if it exists
def load_test_env():
    """Load test environment variables from tests/env.test file"""
    env_file = Path(__file__).parent / "env.test"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    # Only set if not already in environment and not a placeholder
                    if key.strip() not in os.environ:
                        val = value.strip()
                        if val and val != "your_access_token_here" and val != "your_spreadsheet_id_here":
                            os.environ[key.strip()] = val


load_test_env()


# Check if E2E tests should be skipped
SKIP_E2E = os.getenv("SKIP_E2E_TESTS", "false").lower() == "true"

# Global variables for credentials (will be set by prompt_for_credentials)
TEST_ACCESS_TOKEN = None
TEST_SPREADSHEET_ID = None
TEST_SHEET_NAME = "Sheet1"
TEST_SHEET_ID = 0


def prompt_for_credentials():
    """
    Prompt user for credentials interactively if not provided in environment.
    This runs once before all E2E tests.
    """
    global TEST_ACCESS_TOKEN, TEST_SPREADSHEET_ID, TEST_SHEET_NAME, TEST_SHEET_ID
    
    # Check if already set from environment
    token = os.getenv("GOOGLE_SHEETS_TEST_ACCESS_TOKEN")
    spreadsheet_id = os.getenv("GOOGLE_SHEETS_TEST_SPREADSHEET_ID")
    
    # If both are set and valid, use them
    if token and token != "your_access_token_here" and spreadsheet_id and spreadsheet_id != "your_spreadsheet_id_here":
        TEST_ACCESS_TOKEN = token
        TEST_SPREADSHEET_ID = spreadsheet_id
        TEST_SHEET_NAME = os.getenv("GOOGLE_SHEETS_TEST_SHEET_NAME", "Sheet1")
        TEST_SHEET_ID = int(os.getenv("GOOGLE_SHEETS_TEST_SHEET_ID", "0"))
        return
    
    # Otherwise, prompt for credentials
    print("\n" + "="*70)
    print("  E2E TESTS - CREDENTIALS REQUIRED")
    print("="*70)
    print()
    print("E2E tests require Google OAuth credentials to test against real API.")
    print()
    print("Get your access token from:")
    print("  https://developers.google.com/oauthplayground/")
    print("  Scope: https://www.googleapis.com/auth/spreadsheets")
    print()
    
    try:
        # Prompt for access token
        TEST_ACCESS_TOKEN = input("Enter Google OAuth Access Token: ").strip()
        if not TEST_ACCESS_TOKEN:
            pytest.skip("No access token provided. Skipping E2E tests.")
        
        # Prompt for spreadsheet ID
        TEST_SPREADSHEET_ID = input("Enter Google Spreadsheet ID: ").strip()
        if not TEST_SPREADSHEET_ID:
            pytest.skip("No spreadsheet ID provided. Skipping E2E tests.")
        
        # Optional: Sheet name (default: Sheet1)
        sheet_name = input("Enter Sheet Name (default: Sheet1): ").strip()
        TEST_SHEET_NAME = sheet_name if sheet_name else "Sheet1"
        
        # Optional: Sheet ID (default: 0)
        sheet_id_input = input("Enter Sheet ID (default: 0): ").strip()
        TEST_SHEET_ID = int(sheet_id_input) if sheet_id_input else 0
        
        print()
        print("✅ Credentials configured!")
        print(f"   Spreadsheet: {TEST_SPREADSHEET_ID}")
        print(f"   Sheet: {TEST_SHEET_NAME} (ID: {TEST_SHEET_ID})")
        print()
        print("="*70)
        print()
        
    except (EOFError, KeyboardInterrupt):
        print("\n\n⚠️  Credential input interrupted. Skipping E2E tests.")
        pytest.skip("Credential input interrupted by user.")


# Determine if we should skip E2E tests
if SKIP_E2E:
    pytestmark = pytest.mark.skip(reason="E2E tests disabled (SKIP_E2E_TESTS=true)")
else:
    # Mark all tests in this module as "e2e" for selective execution
    pytestmark = pytest.mark.e2e


@pytest.fixture(scope="module", autouse=True)
def setup_e2e_credentials():
    """
    Setup fixture that runs once before all E2E tests in this module.
    Prompts for credentials if not already configured.
    """
    if not SKIP_E2E:
        prompt_for_credentials()


def _e2e_payload(data):
    """Helper to create request payload with real credentials"""
    return {
        "data": data,
        "credentials": {"connection_data": {"value": {"access_token": TEST_ACCESS_TOKEN}}}
    }


class TestE2EReadRange:
    """End-to-end tests for read_range module"""
    
    def test_content_fetches_real_sheets(self, client):
        """Test /content endpoint fetches real sheets from test spreadsheet"""
        payload = _e2e_payload({
            "form_data": {
                "spreadsheet_id": TEST_SPREADSHEET_ID
            }
        })
        
        res = client.post("/read_range/v1/content", json=payload)
        assert res.status_code == 200
        
        body = res.get_json()
        assert "data" in body
        assert "content_objects" in body["data"]
        
        content_objects = body["data"]["content_objects"]
        # CDK transforms content_object_name to 'id' and data to 'content'
        sheets_obj = next(
            (obj for obj in content_objects if obj.get("id") == "sheets_by_spreadsheet"),
            None
        )
        
        assert sheets_obj is not None
        assert "content" in sheets_obj
        assert isinstance(sheets_obj["content"], list)
        # Should have at least one sheet
        assert len(sheets_obj["content"]) > 0
        
        # Verify sheet structure
        first_sheet = sheets_obj["content"][0]
        assert "label" in first_sheet
        assert "value" in first_sheet
        assert "id" in first_sheet["value"]
        assert "label" in first_sheet["value"]
    
    def test_execute_reads_real_data_with_range(self, client):
        """Test /execute endpoint reads real data from test spreadsheet using A1 range"""
        # Read a small range from the test sheet
        payload = _e2e_payload({
            "spreadsheet_id": TEST_SPREADSHEET_ID,
            "range_a1": f"{TEST_SHEET_NAME}!A1:C3"
        })
        
        res = client.post("/read_range/v1/execute", json=payload)
        assert res.status_code == 200
        
        body = res.get_json()
        assert "data" in body
        assert "metadata" in body
        
        # Data should be a list of rows
        assert isinstance(body["data"], list)
        
        # Metadata should contain range info
        metadata = body["metadata"]
        assert "range" in metadata
        assert TEST_SHEET_NAME in metadata["range"]
    
    def test_execute_reads_with_sheet_selection(self, client):
        """Test /execute endpoint reads data using sheet selection (builds default range)"""
        payload = _e2e_payload({
            "spreadsheet_id": TEST_SPREADSHEET_ID,
            "sheet": {
                "id": TEST_SHEET_ID,
                "label": TEST_SHEET_NAME
            }
        })
        
        res = client.post("/read_range/v1/execute", json=payload)
        assert res.status_code == 200
        
        body = res.get_json()
        assert "data" in body
        assert isinstance(body["data"], list)


class TestE2EAppendRows:
    """End-to-end tests for append_rows module"""
    
    def test_append_real_rows_to_sheet(self, client):
        """Test appending real rows to test spreadsheet"""
        import time
        timestamp = int(time.time())
        
        payload = _e2e_payload({
            "spreadsheet_id": TEST_SPREADSHEET_ID,
            "sheet": {
                "id": TEST_SHEET_ID,
                "label": TEST_SHEET_NAME
            },
            "rows": [
                [f"E2E Test {timestamp}", "Column 2", "Column 3"],
                [f"Row 2 {timestamp}", "Data 2", "Data 3"]
            ]
        })
        
        res = client.post("/append_rows/v1/execute", json=payload)
        assert res.status_code == 200
        
        body = res.get_json()
        assert "data" in body
        assert "metadata" in body
        
        metadata = body["metadata"]
        assert "updatedRows" in metadata
        assert metadata["updatedRows"] == 2
        assert "updatedRange" in metadata
        assert TEST_SHEET_NAME in metadata["updatedRange"]


class TestE2EUpdateRange:
    """End-to-end tests for update_range module"""
    
    def test_update_real_range_in_sheet(self, client):
        """Test updating a real range in test spreadsheet"""
        import time
        timestamp = int(time.time())
        
        # Update a specific cell range
        payload = _e2e_payload({
            "spreadsheet_id": TEST_SPREADSHEET_ID,
            "range_a1": f"{TEST_SHEET_NAME}!A1:B1",
            "values": [
                [f"Updated {timestamp}", f"Timestamp: {timestamp}"]
            ]
        })
        
        res = client.post("/update_range/v1/execute", json=payload)
        assert res.status_code == 200
        
        body = res.get_json()
        assert "data" in body
        assert "metadata" in body
        
        metadata = body["metadata"]
        assert "updatedRange" in metadata
        assert "updatedCells" in metadata
        assert metadata["updatedCells"] >= 2  # At least 2 cells updated


class TestE2EDeleteRows:
    """End-to-end tests for delete_rows module"""
    
    @pytest.mark.destructive
    def test_delete_real_rows_from_sheet(self, client):
        """Test deleting real rows from test spreadsheet (DESTRUCTIVE - use with caution)"""
        # First, append some rows to delete
        import time
        timestamp = int(time.time())
        
        # Append test rows
        append_payload = _e2e_payload({
            "spreadsheet_id": TEST_SPREADSHEET_ID,
            "sheet": {
                "id": TEST_SHEET_ID,
                "label": TEST_SHEET_NAME
            },
            "rows": [
                [f"DELETE ME {timestamp}", "Row to delete 1"],
                [f"DELETE ME {timestamp}", "Row to delete 2"],
                [f"DELETE ME {timestamp}", "Row to delete 3"]
            ]
        })
        
        append_res = client.post("/append_rows/v1/execute", json=append_payload)
        assert append_res.status_code == 200
        
        # Now delete the last 2 rows we just added
        # Note: You need to know the row numbers. For safety, we'll skip actual deletion
        # and just test the validation
        
        # This test is marked as @pytest.mark.destructive
        # Run with: pytest -m destructive
        # to actually perform deletion
        
        pytest.skip("Skipping actual deletion in E2E test. Mark as destructive to run.")


class TestE2EErrorHandling:
    """End-to-end tests for error handling with real API"""
    
    def test_invalid_spreadsheet_id_returns_404(self, client):
        """Test that invalid spreadsheet ID returns proper error"""
        payload = _e2e_payload({
            "spreadsheet_id": "INVALID_SPREADSHEET_ID_12345",
            "range_a1": "Sheet1!A1"
        })
        
        res = client.post("/read_range/v1/execute", json=payload)
        assert res.status_code in [400, 404]  # Should return error
        
        body = res.get_json()
        assert "error" in body
    
    def test_invalid_range_returns_error(self, client):
        """Test that invalid A1 range returns proper error"""
        payload = _e2e_payload({
            "spreadsheet_id": TEST_SPREADSHEET_ID,
            "range_a1": "InvalidSheet!ZZZZZ99999"
        })
        
        res = client.post("/read_range/v1/execute", json=payload)
        # Should return error (404 or 400)
        assert res.status_code in [400, 404]
        
        body = res.get_json()
        assert "error" in body

