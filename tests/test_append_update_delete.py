"""Unit tests for append_rows, update_range, and delete_rows modules - using mocked HTTP calls"""


def _payload(data, token="test-token"):
    """Helper to create request payload with mock credentials"""
    return {
        "data": data,
        "credentials": {"connection_data": {"value": {"access_token": token}}}
    }


def test_append_missing_spreadsheet_id_returns_400(client):
    """Test that append_rows returns 400 when spreadsheet_id is missing"""
    res = client.post("/append_rows/v1/execute", json=_payload({}))
    assert res.status_code == 400
    body = res.get_json()
    assert "error" in body


def test_append_missing_sheet_returns_400(client):
    """Test that append_rows returns 400 when sheet is missing"""
    res = client.post("/append_rows/v1/execute", json=_payload({"spreadsheet_id": "abc"}))
    assert res.status_code == 400
    body = res.get_json()
    assert "error" in body


def test_append_success_with_mocked_api(monkeypatch, client):
    """Test that append_rows works with mocked Google API"""
    def mock_post(url, headers=None, params=None, json=None):
        class MockResponse:
            status_code = 200
            
            def raise_for_status(self):
                return None
            
            def json(self):
                return {
                    "spreadsheetId": "abc",
                    "updates": {
                        "updatedRange": "Sheet1!A1:B2",
                        "updatedRows": 2,
                        "updatedCells": 4
                    }
                }
        
        return MockResponse()

    import src.utils.google_sheets as gs
    monkeypatch.setattr(gs._session, "post", mock_post)

    data = {
        "spreadsheet_id": "abc",
        "sheet": {"label": "Sheet1", "id": 0},
        "rows": [["A1", "B1"], ["A2", "B2"]]
    }
    res = client.post("/append_rows/v1/execute", json=_payload(data))
    assert res.status_code == 200
    body = res.get_json()
    assert "data" in body
    assert body.get("metadata", {}).get("updatedRows") == 2


def test_update_missing_spreadsheet_id_returns_400(client):
    """Test that update_range returns 400 when spreadsheet_id is missing"""
    res = client.post("/update_range/v1/execute", json=_payload({}))
    assert res.status_code == 400
    body = res.get_json()
    assert "error" in body


def test_update_missing_range_returns_400(client):
    """Test that update_range returns 400 when range_a1 is missing"""
    res = client.post("/update_range/v1/execute", json=_payload({"spreadsheet_id": "abc"}))
    assert res.status_code == 400
    body = res.get_json()
    assert "error" in body


def test_update_success_with_mocked_api(monkeypatch, client):
    """Test that update_range works with mocked Google API"""
    def mock_put(url, headers=None, params=None, json=None):
        class MockResponse:
            status_code = 200
            
            def raise_for_status(self):
                return None
            
            def json(self):
                return {
                    "spreadsheetId": "abc",
                    "updatedRange": "Sheet1!A1:B2",
                    "updatedRows": 2,
                    "updatedCells": 4
                }
        
        return MockResponse()

    import src.utils.google_sheets as gs
    monkeypatch.setattr(gs._session, "put", mock_put)

    data = {
        "spreadsheet_id": "abc",
        "range_a1": "Sheet1!A1:B2",
        "values": [["Updated1", "Updated2"], ["Updated3", "Updated4"]]
    }
    res = client.post("/update_range/v1/execute", json=_payload(data))
    assert res.status_code == 200
    body = res.get_json()
    assert "data" in body
    assert body.get("metadata", {}).get("updatedRows") == 2


def test_delete_missing_spreadsheet_id_returns_400(client):
    """Test that delete_rows returns 400 when spreadsheet_id is missing"""
    res = client.post("/delete_rows/v1/execute", json=_payload({}))
    assert res.status_code == 400
    body = res.get_json()
    assert "error" in body


def test_delete_missing_sheet_returns_400(client):
    """Test that delete_rows returns 400 when sheet is missing"""
    res = client.post("/delete_rows/v1/execute", json=_payload({"spreadsheet_id": "abc"}))
    assert res.status_code == 400
    body = res.get_json()
    assert "error" in body


def test_delete_success_with_mocked_api(monkeypatch, client):
    """Test that delete_rows works with mocked Google API"""
    def mock_post(url, headers=None, json=None):
        class MockResponse:
            status_code = 200
            
            def raise_for_status(self):
                return None
            
            def json(self):
                return {
                    "spreadsheetId": "abc",
                    "replies": [{}]
                }
        
        return MockResponse()

    import src.utils.google_sheets as gs
    monkeypatch.setattr(gs._session, "post", mock_post)

    data = {
        "spreadsheet_id": "abc",
        "sheet": {"label": "Sheet1", "id": "0"},  # ID should be string in the data
        "row_start": 2,
        "row_end": 5
    }
    res = client.post("/delete_rows/v1/execute", json=_payload(data))
    assert res.status_code == 200
    body = res.get_json()
    assert "data" in body
    # Note: The key is 'deletedRowsCount' not 'deletedRows' (check response_helpers.py)
    metadata = body.get("metadata", {})
    # Either deletedRows or deletedRowsCount could be used
    deleted_count = metadata.get("deletedRows") or metadata.get("deletedRowsCount")
    assert deleted_count == 4  # rows 2-5 inclusive


