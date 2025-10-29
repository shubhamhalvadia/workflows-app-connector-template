"""Unit tests for read_range module - using mocked HTTP calls"""
import json


def _payload(data, token="test-token"):
    """Helper to create request payload with mock credentials"""
    return {
        "data": data,
        "credentials": {"connection_data": {"value": {"access_token": token}}}
    }


def test_content_without_spreadsheet_id_returns_empty(client):
    """Test that /content returns empty list when spreadsheet_id is missing"""
    res = client.post("/read_range/v1/content", json=_payload({"form_data": {}}))
    assert res.status_code == 200
    body = res.get_json()
    
    # Response.content() returns {"data": {"content_objects": [...]}}
    assert "data" in body
    assert "content_objects" in body["data"]
    objs = body["data"]["content_objects"]
    
    # Find the sheets_by_spreadsheet object and verify it's empty
    # CDK transforms content_object_name to 'id' and data to 'content'
    sheets_obj = next((o for o in objs if o.get("id") == "sheets_by_spreadsheet"), None)
    assert sheets_obj is not None
    assert sheets_obj.get("content") == []


def test_execute_missing_spreadsheet_id_returns_400(client):
    """Test that /execute returns 400 when spreadsheet_id is missing"""
    res = client.post("/read_range/v1/execute", json=_payload({}))
    assert res.status_code == 400
    body = res.get_json()
    assert body.get("error")


def test_execute_with_sheet_builds_default_range_and_returns_values(monkeypatch, client):
    """Test that /execute builds default range from sheet and returns values"""
    # Mock the Session.get method (NOT requests.get, since we now use _session)
    def mock_get(url, headers=None, params=None):
        class MockResponse:
            status_code = 200
            text = '{"range": "Sheet1!A:Z1:100", "majorDimension": "ROWS", "values": [["A"]]}'
            
            def raise_for_status(self):
                return None
            
            def json(self):
                return {"range": "Sheet1!A:Z1:100", "majorDimension": "ROWS", "values": [["A"]]}
        
        return MockResponse()

    # Patch _session.get (not requests.get) since we use connection pooling
    import src.utils.google_sheets as gs
    monkeypatch.setattr(gs._session, "get", mock_get)

    data = {"spreadsheet_id": "abc", "sheet": {"label": "Sheet1", "id": 1}}
    res = client.post("/read_range/v1/execute", json=_payload(data))
    assert res.status_code == 200
    body = res.get_json()
    assert body.get("data") == [["A"]]
    assert "metadata" in body


def test_execute_with_range_a1_validates_and_returns_values(monkeypatch, client):
    """Test that /execute validates A1 notation and returns values"""
    def mock_get(url, headers=None, params=None):
        class MockResponse:
            status_code = 200
            text = '{"range": "Sheet1!A1:B2", "majorDimension": "ROWS", "values": [["A1", "B1"], ["A2", "B2"]]}'
            
            def raise_for_status(self):
                return None
            
            def json(self):
                return {"range": "Sheet1!A1:B2", "majorDimension": "ROWS", "values": [["A1", "B1"], ["A2", "B2"]]}
        
        return MockResponse()

    import src.utils.google_sheets as gs
    monkeypatch.setattr(gs._session, "get", mock_get)

    data = {"spreadsheet_id": "abc", "range_a1": "Sheet1!A1:B2"}
    res = client.post("/read_range/v1/execute", json=_payload(data))
    assert res.status_code == 200
    body = res.get_json()
    assert body.get("data") == [["A1", "B1"], ["A2", "B2"]]
    assert body.get("metadata", {}).get("range") == "Sheet1!A1:B2"


