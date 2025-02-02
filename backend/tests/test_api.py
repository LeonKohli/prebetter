

def test_list_alerts(client):
    """Test the alerts listing endpoint"""
    response = client.get("/api/v1/alerts")
    assert response.status_code == 200

    data = response.json()
    assert "total" in data
    assert "items" in data
    assert isinstance(data["items"], list)

    if len(data["items"]) > 0:
        alert = data["items"][0]
        assert "alert_id" in alert
        assert "classification_text" in alert
        assert "severity" in alert
        assert "source_ipv4" in alert
        assert "target_ipv4" in alert
        assert "analyzer" in alert


def test_alert_detail(client):
    """Test the alert detail endpoint with a known alert ID"""
    # Get first alert from list to use a real ID
    list_response = client.get("/api/v1/alerts")
    alerts = list_response.json()["items"]

    if len(alerts) > 0:
        alert_id = alerts[0]["alert_id"]
        response = client.get(f"/api/v1/alerts/{alert_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["alert_id"] == alert_id
        assert "severity" in data
        assert "classification_text" in data
        assert "source" in data
        assert "target" in data
        assert "analyzer" in data
        assert "references" in data
        assert "services" in data
        assert "additional_data" in data


def test_alert_detail_not_found(client):
    """Test the alert detail endpoint with non-existent alert"""
    response = client.get("/api/v1/alerts/99999999")
    assert response.status_code == 404


def test_alert_filtering(client):
    """Test alert filtering options"""
    # Test severity filter
    response = client.get("/api/v1/alerts?severity=high")
    assert response.status_code == 200
    data = response.json()
    if len(data["items"]) > 0:
        assert all(alert["severity"] == "high" for alert in data["items"])

    # Test date range filter
    # Use a date from the past to ensure we have data
    start_date = "2024-01-01T00:00:00Z"  # Use simple ISO format with Z for UTC
    response = client.get(f"/api/v1/alerts?start_date={start_date}")
    if response.status_code != 200:
        print(f"Error response: {response.json()}")
    assert response.status_code == 200

    # Test classification filter
    response = client.get("/api/v1/alerts?classification=FILE")
    assert response.status_code == 200


def test_statistics_summary(client):
    """Test the statistics summary endpoint"""
    response = client.get("/api/v1/statistics/summary")
    assert response.status_code == 200

    data = response.json()
    assert "severity_distribution" in data
    assert "top_classifications" in data
    assert "top_source_ips" in data
    assert data["time_range_hours"] == 24
    assert isinstance(data["severity_distribution"], dict)
    assert isinstance(data["top_classifications"], dict)
    assert isinstance(data["top_source_ips"], dict)


def test_unique_values_endpoints(client):
    """Test endpoints that return unique values"""
    # Test classifications
    response = client.get("/api/v1/classifications/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

    # Test severities
    response = client.get("/api/v1/impacts/severities/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

    # Test analyzers
    response = client.get("/api/v1/analyzers/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_sorting(client):
    """Test alert sorting options"""
    sort_fields = ["detect_time", "create_time", "severity", "classification"]
    sort_orders = ["asc", "desc"]

    for sort_field in sort_fields:
        for sort_order in sort_orders:
            response = client.get(
                f"/api/v1/alerts?sort_by={sort_field}&sort_order={sort_order}"
            )
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data["items"], list)


def test_pagination(client):
    """Test alert pagination"""
    # Test first page
    response = client.get("/api/v1/alerts?page=1&size=10")
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 1
    assert data["size"] == 10

    # Test invalid page
    response = client.get("/api/v1/alerts?page=0")
    assert response.status_code == 422

    # Test invalid size
    response = client.get("/api/v1/alerts?size=1000")
    assert response.status_code == 422


def test_payload_truncation(client):
    """Test payload truncation option"""
    # Get first alert from list
    list_response = client.get("/api/v1/alerts")
    alerts = list_response.json()["items"]

    if len(alerts) > 0:
        alert_id = alerts[0]["alert_id"]

        # Test with truncation
        response = client.get(f"/api/v1/alerts/{alert_id}?truncate_payload=true")
        assert response.status_code == 200
        truncated_data = response.json()

        # Test without truncation
        response = client.get(f"/api/v1/alerts/{alert_id}?truncate_payload=false")
        assert response.status_code == 200
        full_data = response.json()

        if "payload" in truncated_data.get(
            "additional_data", {}
        ) and "payload" in full_data.get("additional_data", {}):
            truncated_len = len(truncated_data["additional_data"]["payload"])
            full_len = len(full_data["additional_data"]["payload"])
            if truncated_len < full_len:
                assert truncated_data["additional_data"]["payload"].endswith("...")


def test_alert_timeline(client):
    """Test the alert timeline endpoint"""
    # Test with default parameters
    response = client.get("/api/v1/timeline")
    if response.status_code != 200:
        print(f"Error response: {response.json()}")
    assert response.status_code == 200
    data = response.json()
    assert "time_frame" in data
    assert "start_date" in data
    assert "end_date" in data
    assert "data" in data
    assert isinstance(data["data"], list)

    # Test with specific time frame
    response = client.get("/api/v1/timeline?time_frame=hour")
    if response.status_code != 200:
        print(f"Error response: {response.json()}")
    assert response.status_code == 200
    hourly_data = response.json()
    assert hourly_data["time_frame"] == "hour"

    # Test with date range
    start_date = "2024-01-01T00:00:00Z"
    end_date = "2024-01-02T00:00:00Z"
    response = client.get(
        f"/api/v1/timeline?start_date={start_date}&end_date={end_date}"
    )
    if response.status_code != 200:
        print(f"Error response: {response.json()}")
    assert response.status_code == 200

    # Test with filters
    response = client.get("/api/v1/timeline?severity=high&time_frame=day")
    if response.status_code != 200:
        print(f"Error response: {response.json()}")
    assert response.status_code == 200
    filtered_data = response.json()
    assert filtered_data["time_frame"] == "day"

    # Test all time frames
    time_frames = ["hour", "day", "week", "month"]
    for frame in time_frames:
        response = client.get(f"/api/v1/timeline?time_frame={frame}")
        if response.status_code != 200:
            print(f"Error response for {frame}: {response.json()}")
        assert response.status_code == 200
        data = response.json()
        assert data["time_frame"] == frame
