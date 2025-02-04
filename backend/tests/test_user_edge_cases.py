import uuid


def test_create_user_validation(superuser_client):
    """
    Test user creation with invalid data to ensure proper validation.
    """
    # Test with invalid email
    payload = {
        "username": "testuser3",
        "password": "testpassword3",
        "email": "invalid-email",
        "full_name": "Test User 3"
    }
    response = superuser_client.post("/api/v1/users/", json=payload)
    assert response.status_code == 422, "Invalid email format was accepted"

    # Test with missing required fields
    payload = {
        "username": "testuser3",
        "email": "test3@example.com"
    }
    response = superuser_client.post("/api/v1/users/", json=payload)
    assert response.status_code == 422, "Missing required fields were accepted"

def test_user_not_found_scenarios(superuser_client):
    """
    Test scenarios where users are not found.
    """
    non_existent_id = str(uuid.uuid4())

    # Test get non-existent user
    response = superuser_client.get(f"/api/v1/users/{non_existent_id}")
    assert response.status_code == 404, "Non-existent user lookup should return 404"

    # Test update non-existent user
    update_payload = {
        "email": "updated@example.com",
        "full_name": "Updated Name"
    }
    response = superuser_client.put(f"/api/v1/users/{non_existent_id}", json=update_payload)
    assert response.status_code == 404, "Non-existent user update should return 404"

    # Test delete non-existent user
    response = superuser_client.delete(f"/api/v1/users/{non_existent_id}")
    assert response.status_code == 404, "Non-existent user deletion should return 404"

def test_concurrent_user_operations(superuser_client, test_db):
    """
    Test handling of concurrent user operations.
    """
    # Create initial user
    payload = {
        "username": "concurrent_user",
        "password": "testpassword",
        "email": "concurrent@example.com",
        "full_name": "Concurrent User"
    }
    response = superuser_client.post("/api/v1/users/", json=payload)
    assert response.status_code == 200
    user_data = response.json()  # noqa

    # Try to create another user with same username/email while the first one exists
    concurrent_payload = {
        "username": "concurrent_user",
        "password": "testpassword2",
        "email": "concurrent@example.com",
        "full_name": "Concurrent User 2"
    }
    response = superuser_client.post("/api/v1/users/", json=concurrent_payload)
    assert response.status_code == 400, "Concurrent user creation with same username/email should fail"

    # Try to update another user to have the same username/email
    another_user_payload = {
        "username": "another_user",
        "password": "testpassword",
        "email": "another@example.com",
        "full_name": "Another User"
    }
    response = superuser_client.post("/api/v1/users/", json=another_user_payload)
    assert response.status_code == 200
    another_user = response.json()

    # Try to update the second user to have the same username as the first
    update_payload = {
        "username": "concurrent_user"
    }
    response = superuser_client.put(f"/api/v1/users/{another_user['id']}", json=update_payload)
    assert response.status_code == 400, "Update to existing username should fail"

    # Try to update the second user to have the same email as the first
    update_payload = {
        "email": "concurrent@example.com"
    }
    response = superuser_client.put(f"/api/v1/users/{another_user['id']}", json=update_payload)
    assert response.status_code == 400, "Update to existing email should fail"

def test_user_listing_pagination(superuser_client, test_db):
    """
    Test user listing with pagination.
    """
    # Create multiple users
    for i in range(15):  # Create enough users to test pagination
        payload = {
            "username": f"pageuser{i}",
            "password": "testpassword",
            "email": f"page{i}@example.com",
            "full_name": f"Page User {i}"
        }
        response = superuser_client.post("/api/v1/users/", json=payload)
        assert response.status_code == 200

    # Test first page
    response = superuser_client.get("/api/v1/users/?skip=0&limit=10")
    assert response.status_code == 200
    first_page = response.json()
    assert len(first_page) <= 10, "First page should have at most 10 users"

    # Test second page
    response = superuser_client.get("/api/v1/users/?skip=10&limit=10")
    assert response.status_code == 200
    second_page = response.json()
    assert len(second_page) > 0, "Second page should have some users"

    # Verify no duplicate users between pages
    first_page_ids = {user["id"] for user in first_page}
    second_page_ids = {user["id"] for user in second_page}
    assert not first_page_ids.intersection(second_page_ids), "Pages should not have duplicate users"

def test_invalid_pagination_parameters(superuser_client):
    """
    Test user listing with invalid pagination parameters.
    """
    # Test negative skip
    response = superuser_client.get("/api/v1/users/?skip=-1&limit=10")
    assert response.status_code == 422, "Negative skip value should be rejected"

    # Test negative limit
    response = superuser_client.get("/api/v1/users/?skip=0&limit=-1")
    assert response.status_code == 422, "Negative limit value should be rejected"

    # Test zero limit
    response = superuser_client.get("/api/v1/users/?skip=0&limit=0")
    assert response.status_code == 422, "Zero limit value should be rejected"

    # Test excessively large limit
    response = superuser_client.get("/api/v1/users/?skip=0&limit=1001")
    assert response.status_code == 422, "Excessive limit value should be rejected"

def test_user_update_validation(superuser_client, test_db):
    """
    Test user update with various validation scenarios.
    """
    # Create a user to update
    payload = {
        "username": "updatetest",
        "password": "testpassword",
        "email": "updatetest@example.com",
        "full_name": "Update Test User"
    }
    response = superuser_client.post("/api/v1/users/", json=payload)
    assert response.status_code == 200
    user_data = response.json()

    # Test update with invalid email
    update_payload = {
        "email": "invalid-email"
    }
    response = superuser_client.put(f"/api/v1/users/{user_data['id']}", json=update_payload)
    assert response.status_code == 422, "Invalid email format was accepted in update"

    # Test update with empty strings
    update_payload = {
        "username": "",
        "email": "valid@example.com"
    }
    response = superuser_client.put(f"/api/v1/users/{user_data['id']}", json=update_payload)
    assert response.status_code == 422, "Empty username was accepted"

    # Test update with only whitespace in optional fields
    update_payload = {
        "full_name": "   "
    }
    response = superuser_client.put(f"/api/v1/users/{user_data['id']}", json=update_payload)
    assert response.status_code == 422, "Whitespace-only full name was accepted" 