import csv
import io
import pytest
from datetime import datetime, timedelta, UTC

def get_csv_rows(response_text: str):
    """Helper function to read CSV content into a list of rows."""
    f = io.StringIO(response_text)
    reader = csv.reader(f)
    return list(reader)


def test_export_csv_default(auth_client):
    """
    Test exporting alerts in CSV format with no filters.

    This test verifies:
      - The endpoint returns HTTP 200.
      - The Content-Type and Content-Disposition headers are set correctly.
      - The CSV header row matches the expected header.
      - Each data row (if any) has the same number of columns as the header.
      - The data types of each column are correct.
    """
    response = auth_client.get("/api/v1/export/alerts/csv")
    assert response.status_code == 200, "Expected status code 200 for CSV export"

    # Check headers for CSV response
    content_type = response.headers.get("Content-Type", "")
    assert content_type.startswith("text/csv"), (
        f"Expected text/csv content-type, got {content_type}"
    )
    content_disp = response.headers.get("Content-Disposition", "")
    assert "alerts.csv" in content_disp, (
        "Content-Disposition header should indicate alerts.csv"
    )

    # Decode the CSV content and check header row
    csv_text = response.content.decode("utf-8")
    rows = get_csv_rows(csv_text)
    expected_header = [
        "Alert ID",
        "Message ID",
        "Detect Time",
        "Create Time",
        "Classification",
        "Severity",
        "Source IP",
        "Target IP",
        "Analyzer Name",
        "Analyzer Host",
        "Analyzer Model",
    ]
    assert rows, "CSV output should not be empty"
    assert rows[0] == expected_header, (
        f"CSV header does not match expected header. Got {rows[0]}"
    )

    # If any data rows exist, validate their structure and content
    for row in rows[1:]:
        assert len(row) == len(expected_header), (
            "CSV data row does not match header length"
        )
        # Validate data types and formats
        if row[2]:  # Detect Time
            try:
                dt = datetime.fromisoformat(row[2])
                assert dt.tzinfo is not None, "Datetime should be timezone-aware"
            except ValueError:
                pytest.fail(f"Invalid datetime format for Detect Time: {row[2]}")
        if row[3]:  # Create Time
            try:
                dt = datetime.fromisoformat(row[3])
                assert dt.tzinfo is not None, "Datetime should be timezone-aware"
            except ValueError:
                pytest.fail(f"Invalid datetime format for Create Time: {row[3]}")


def test_export_csv_with_filters(auth_client):
    """Test exporting alerts with various filter combinations."""
    # Test with single filter
    response = auth_client.get("/api/v1/export/alerts/csv?severity=high")
    assert response.status_code == 200
    rows = get_csv_rows(response.content.decode("utf-8"))
    if len(rows) > 1:  # If there are data rows
        assert all(row[5] == "high" for row in rows[1:]), "All rows should have high severity"

    # Test with multiple filters
    end_date = datetime.now(UTC)
    start_date = end_date - timedelta(days=7)
    params = {
        "severity": "high",
        "classification": "scan",
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "source_ip": "192.168.1.1",
        "target_ip": "10.0.0.1",
        "analyzer_model": "test-model"
    }
    response = auth_client.get("/api/v1/export/alerts/csv", params=params)
    assert response.status_code == 200


def test_export_csv_no_results(auth_client):
    """
    Test exporting alerts in CSV format using filters that yield no results.

    We use a far-future date range to force an empty result.
    The CSV output should contain only the header row.
    """
    future_start = "2100-01-01T00:00:00"
    future_end = "2100-12-31T23:59:59"
    response = auth_client.get(
        f"/api/v1/export/alerts/csv?start_date={future_start}&end_date={future_end}"
    )
    assert response.status_code == 200, (
        "Expected status code 200 even when no alerts match filters"
    )

    csv_text = response.content.decode("utf-8")
    rows = get_csv_rows(csv_text)
    expected_header = [
        "Alert ID",
        "Message ID",
        "Detect Time",
        "Create Time",
        "Classification",
        "Severity",
        "Source IP",
        "Target IP",
        "Analyzer Name",
        "Analyzer Host",
        "Analyzer Model",
    ]
    assert rows[0] == expected_header, "CSV header does not match expected header"
    # Only the header row should be present
    assert len(rows) == 1, f"Expected only header row, but got {len(rows)} rows"


def test_export_authentication(client):
    """Test that the export endpoint requires authentication."""
    # Test without authentication
    response = client.get("/api/v1/export/alerts/csv")
    assert response.status_code == 401
    assert "Not authenticated" in response.json()["detail"]


def test_export_unsupported_format(auth_client):
    """
    Test that requesting an unsupported export format (e.g. 'json') returns a 422 error.
    """
    response = auth_client.get(
        "/api/v1/export/alerts/json"
    )  # using 'json' as an unsupported format
    assert response.status_code == 422, "Unsupported export format should return 422"
    data = response.json()
    # FastAPI validation errors return a detail list in the response
    assert "detail" in data, "Expected validation error response to contain 'detail' key"
    errors = data["detail"]
    assert isinstance(errors, list), "Expected validation error details to be a list"
    assert any(
        error.get("msg") == "Input should be 'csv'"
        for error in errors
    ), "Error message should indicate only CSV format is supported"


def test_export_invalid_date(auth_client):
    """
    Test that providing an invalid date for start_date results in a validation error.
    """
    response = auth_client.get("/api/v1/export/alerts/csv?start_date=not-a-date")
    # FastAPI typically returns a 422 Unprocessable Entity for validation errors.
    assert response.status_code in (400, 422), (
        "Invalid date format should result in a validation error"
    )


def test_export_invalid_alert_ids(auth_client):
    """
    Test that providing non-integer alert_ids returns a validation error.

    The alert_ids query parameter is expected to be a list of integers.
    """
    response = auth_client.get("/api/v1/export/alerts/csv?alert_ids=abc")
    assert response.status_code in (400, 422), (
        "Non-integer alert_ids should be rejected with a validation error"
    )


def test_export_specific_alerts(auth_client):
    """Test exporting specific alerts by ID."""
    # First get some alert IDs from the alerts endpoint
    alerts_response = auth_client.get("/api/v1/alerts/?page=1&size=2")
    assert alerts_response.status_code == 200
    alerts_data = alerts_response.json()
    
    if alerts_data["items"]:
        alert_ids_to_export = [item["id"] for item in alerts_data["items"]]
        # Test export with specific alert IDs
        # FastAPI TestClient handles list query parameters correctly
        params = [("alert_ids", alert_id) for alert_id in alert_ids_to_export]
        response = auth_client.get("/api/v1/export/alerts/csv", params=params)
        assert response.status_code == 200
        
        rows = get_csv_rows(response.content.decode("utf-8"))
        # Check if the header exists
        assert len(rows) > 0, "CSV should have at least a header row"
        exported_ids = {row[0] for row in rows[1:]} # Alert ID is the first column
        
        # Verify that all requested alert IDs are present in the export
        assert all(str(req_id) in exported_ids for req_id in alert_ids_to_export), (
            f"Not all requested alert IDs ({alert_ids_to_export}) were found in the export ({exported_ids})"
        )
            
        # Optionally, verify that ONLY requested alerts are present (if filters work exclusively)
        # assert len(rows[1:]) == len(alert_ids_to_export), \
        #     "Export should contain only the specified alert IDs"
    else:
        pytest.skip("No alerts found to test specific export by ID")
