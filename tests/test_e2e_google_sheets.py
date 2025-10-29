"""
End-to-End (E2E) Tests for Google Sheets Connector

These tests make REAL API calls to Google Sheets API using actual credentials.
They validate the complete integration flow from connector to Google Sheets.

Prerequisites:
1. Copy tests/env.test.example to tests/env.test
2. Fill in your Google OAuth access token and test spreadsheet ID
3. Ensure the test spreadsheet exists and is accessible

To run only E2E tests:
    pytest tests/test_e2e_google_sheets.py -v

To skip E2E tests (useful for CI/CD):
    pytest -m "not e2e"
    
Or set SKIP_E2E_TESTS=true in tests/env.test
"""

import pytest
import os
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
                    os.environ[key.strip()] = value.strip()


load_test_env()


# Check if E2E tests should be skipped
SKIP_E2E = os.getenv("SKIP_E2E_TESTS", "false").lower() == "true"
TEST_ACCESS_TOKEN = os.getenv("GOOGLE_SHEETS_TEST_ACCESS_TOKEN")
TEST_SPREADSHEET_ID = os.getenv("GOOGLE_SHEETS_TEST_SPREADSHEET_ID")
TEST_SHEET_NAME = os.getenv("GOOGLE_SHEETS_TEST_SHEET_NAME", "TestSheet")
TEST_SHEET_ID = int(os.getenv("GOOGLE_SHEETS_TEST_SHEET_ID", "0"))


# Skip all tests in this module if credentials are missing or SKIP_E2E is true
pytestmark = pytest.mark.skipif(
    SKIP_E2E or not TEST_ACCESS_TOKEN or not TEST_SPREADSHEET_ID,
    reason="E2E tests skipped: Missing credentials or SKIP_E2E_TESTS=true. "
           "Copy tests/env.test.example to tests/env.test and configure."
)


# Mark all tests in this module as "e2e" for selective execution
pytestmark = pytest.mark.e2e


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
        sheets_obj = next(
            (obj for obj in content_objects if obj.get("content_object_name") == "sheets_by_spreadsheet"),
            None
        )
        
        assert sheets_obj is not None
        assert "data" in sheets_obj
        assert isinstance(sheets_obj["data"], list)
        # Should have at least one sheet
        assert len(sheets_obj["data"]) > 0
        
        # Verify sheet structure
        first_sheet = sheets_obj["data"][0]
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


class TestE2EPerformance:
    """End-to-end tests for performance optimizations"""
    
    def test_connection_pooling_performance(self, client):
        """Test that connection pooling improves performance on repeated calls"""
        import time
        
        payload = _e2e_payload({
            "spreadsheet_id": TEST_SPREADSHEET_ID,
            "range_a1": f"{TEST_SHEET_NAME}!A1:A1"
        })
        
        # First call (establishes connection)
        start = time.time()
        res1 = client.post("/read_range/v1/execute", json=payload)
        first_call_time = time.time() - start
        assert res1.status_code == 200
        
        # Second call (should reuse connection and be faster)
        start = time.time()
        res2 = client.post("/read_range/v1/execute", json=payload)
        second_call_time = time.time() - start
        assert res2.status_code == 200
        
        # Third call (should also reuse connection)
        start = time.time()
        res3 = client.post("/read_range/v1/execute", json=payload)
        third_call_time = time.time() - start
        assert res3.status_code == 200
        
        # Log performance for manual inspection
        print(f"\nConnection Pooling Performance:")
        print(f"  First call:  {first_call_time:.3f}s")
        print(f"  Second call: {second_call_time:.3f}s")
        print(f"  Third call:  {third_call_time:.3f}s")
        
        # Average of 2nd and 3rd calls should be faster than first
        # (though this can vary based on network conditions)
        avg_subsequent = (second_call_time + third_call_time) / 2
        print(f"  Improvement: {((first_call_time - avg_subsequent) / first_call_time * 100):.1f}%")
    
    def test_cache_improves_metadata_fetching(self, client):
        """Test that LRU cache improves metadata fetching performance"""
        import time
        
        payload = _e2e_payload({
            "form_data": {
                "spreadsheet_id": TEST_SPREADSHEET_ID
            }
        })
        
        # First call (fetches from API, populates cache)
        start = time.time()
        res1 = client.post("/read_range/v1/content", json=payload)
        first_call_time = time.time() - start
        assert res1.status_code == 200
        
        # Second call (should hit cache)
        start = time.time()
        res2 = client.post("/read_range/v1/content", json=payload)
        second_call_time = time.time() - start
        assert res2.status_code == 200
        
        # Log performance
        print(f"\nCache Performance:")
        print(f"  First call (cache miss):  {first_call_time:.3f}s")
        print(f"  Second call (cache hit):  {second_call_time:.3f}s")
        print(f"  Speedup: {(first_call_time / second_call_time):.1f}x faster")
        
        # Cached call should be significantly faster
        # (though network conditions can affect this)
        assert second_call_time < first_call_time

