import uuid
import pytest

from app.models.users import User
from app.core.security import get_password_hash

# Define test data for a superuser.
TEST_SUPERUSER = {
    "username": "admin",
    "password": "admin",  # Match the password from init_db.py
    "email": "admin@example.com",
    "full_name": "Admin User",
}

# Define test data for a new (normal) user.
TEST_USER_PAYLOAD = {
    "username": "newuser",
    "password": "newpassword",
    "email": "newuser@example.com",
    "full_name": "New User",
}


@pytest.fixture
def superuser(test_db):
    """
    Create (or retrieve if already exists) a superuser in the test database.
    """
    db = test_db
    existing = (
        db.query(User).filter(User.username == TEST_SUPERUSER["username"]).first()
    )
    if existing:
        # Update password hash to ensure it matches test password
        existing.hashed_password = get_password_hash(TEST_SUPERUSER["password"])
        db.commit()
        db.refresh(existing)
        return existing

    user = User(
        id=str(uuid.uuid4()),
        username=TEST_SUPERUSER["username"],
        email=TEST_SUPERUSER["email"],
        full_name=TEST_SUPERUSER["full_name"],
        hashed_password=get_password_hash(TEST_SUPERUSER["password"]),
        is_superuser=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def superuser_token(client, superuser):
    """
    Log in as the superuser and return an access token.
    """
    response = client.post(
        "/api/v1/auth/token",
        data={
            "username": TEST_SUPERUSER["username"],
            "password": TEST_SUPERUSER["password"],
        },
    )
    assert response.status_code == 200, f"Token creation failed: {response.text}"
    return response.json()["access_token"]


@pytest.fixture
def superuser_client(client, superuser_token):
    """
    Return a TestClient instance with the superuser's Authorization header set.
    """
    client.headers["Authorization"] = f"Bearer {superuser_token}"
    return client


def test_create_user(superuser_client, test_db):
    """
    Test that a superuser can create a new user.
    """
    payload = {
        "username": "testuser2",
        "password": "testpassword2",
        "email": "testuser2@example.com",
        "full_name": "Test User 2",
    }
    response = superuser_client.post("/api/v1/users/", json=payload)
    assert response.status_code == 200, f"Create user failed: {response.text}"
    data = response.json()
    assert data["username"] == payload["username"]
    assert data["email"] == payload["email"]
    assert data["full_name"] == payload["full_name"]
    # Note: The returned UserSchema likely does not include the hashed password.


def test_create_user_duplicate(superuser_client, test_db):
    """
    Test that trying to create a user with a duplicate username or email returns a 400 error.
    """
    payload = {
        "username": "dupuser",
        "password": "duppassword",
        "email": "dupuser@example.com",
        "full_name": "Dup User",
    }
    # First creation should succeed.
    response = superuser_client.post("/api/v1/users/", json=payload)
    assert response.status_code == 200, f"Initial create failed: {response.text}"

    # Attempt to create a user with the same username but a different email.
    payload_duplicate_username = payload.copy()
    payload_duplicate_username["email"] = "other@example.com"
    response_dup = superuser_client.post(
        "/api/v1/users/", json=payload_duplicate_username
    )
    assert response_dup.status_code == 400, "Duplicate username allowed"

    # Attempt to create a user with the same email but a different username.
    payload_duplicate_email = payload.copy()
    payload_duplicate_email["username"] = "anotheruser"
    response_dup_email = superuser_client.post(
        "/api/v1/users/", json=payload_duplicate_email
    )
    assert response_dup_email.status_code == 400, "Duplicate email allowed"


def test_list_users(superuser_client):
    """
    Test that a superuser can list all users.
    """
    response = superuser_client.get("/api/v1/users/")
    assert response.status_code == 200, f"List users failed: {response.text}"
    data = response.json()
    # Check the new response structure
    assert "items" in data
    assert "pagination" in data
    assert isinstance(data["items"], list)
    # Check that the superuser is present in the returned list.
    usernames = [user["username"] for user in data["items"]]
    assert TEST_SUPERUSER["username"] in usernames


def test_get_user(superuser_client):
    """
    Test that a superuser can retrieve details for a specific user.
    """
    # Create a user to later retrieve.
    payload = {
        "username": "detailuser",
        "password": "detailpass",
        "email": "detailuser@example.com",
        "full_name": "Detail User",
    }
    create_resp = superuser_client.post("/api/v1/users/", json=payload)
    assert create_resp.status_code == 200, f"User creation failed: {create_resp.text}"
    created_user = create_resp.json()
    user_id = created_user["id"]

    # Retrieve the user details.
    get_resp = superuser_client.get(f"/api/v1/users/{user_id}")
    assert get_resp.status_code == 200, f"Get user failed: {get_resp.text}"
    data = get_resp.json()
    assert data["username"] == payload["username"]
    assert data["email"] == payload["email"]


def test_update_user(superuser_client):
    """
    Test that a superuser can update a user's details (including password).
    """
    # Create a user to update.
    payload = {
        "username": "updateuser",
        "password": "updatepass",
        "email": "updateuser@example.com",
        "full_name": "Update User",
    }
    create_resp = superuser_client.post("/api/v1/users/", json=payload)
    assert create_resp.status_code == 200, f"User creation failed: {create_resp.text}"
    created_user = create_resp.json()
    user_id = created_user["id"]

    # Prepare update payload.
    update_payload = {
        "email": "updated@example.com",
        "full_name": "Updated Name",
        "password": "newpassword",
    }
    update_resp = superuser_client.put(f"/api/v1/users/{user_id}", json=update_payload)
    assert update_resp.status_code == 200, f"Update user failed: {update_resp.text}"
    updated_user = update_resp.json()
    assert updated_user["email"] == update_payload["email"]
    assert updated_user["full_name"] == update_payload["full_name"]

    # Verify that the user can now log in with the new password.
    login_resp = superuser_client.post(
        "/api/v1/auth/token",
        data={"username": payload["username"], "password": update_payload["password"]},
    )
    assert login_resp.status_code == 200, "Login with new password failed"


def test_delete_user(superuser_client):
    """
    Test that a superuser can delete a non-superuser user.
    """
    # Create a normal user to delete.
    payload = {
        "username": "deleteuser",
        "password": "deletepass",
        "email": "deleteuser@example.com",
        "full_name": "Delete User",
    }
    create_resp = superuser_client.post("/api/v1/users/", json=payload)
    assert create_resp.status_code == 200, f"User creation failed: {create_resp.text}"
    created_user = create_resp.json()
    user_id = created_user["id"]

    # Delete the user.
    delete_resp = superuser_client.delete(f"/api/v1/users/{user_id}")
    assert delete_resp.status_code == 204, f"Delete user failed: {delete_resp.text}"

    # Verify that the deleted user cannot be retrieved.
    get_resp = superuser_client.get(f"/api/v1/users/{user_id}")
    assert get_resp.status_code == 404, "Deleted user still accessible"


def test_delete_last_superuser(superuser_client, superuser):
    """
    Test that attempting to delete the last remaining superuser fails.
    """
    user_id = superuser.id
    delete_resp = superuser_client.delete(f"/api/v1/users/{user_id}")
    assert delete_resp.status_code == 400, "Allowed deletion of the last superuser"
    detail = delete_resp.json().get("detail", "")
    assert "Cannot delete the last superuser" in detail


def test_change_password(auth_client):
    """
    Test that a user can change their own password.
    The endpoint is expected to return a 204 No Content on success.
    """
    # First, attempt with an incorrect current password.
    wrong_resp = auth_client.post(
        "/api/v1/users/change-password",
        json={"current_password": "wrongpassword", "new_password": "newtestpassword"},
    )
    assert wrong_resp.status_code == 400, (
        "Allowed password change with incorrect current password"
    )

    # Now, change with the correct current password.
    # Note: The TEST_USER from conftest (created via test_db fixture) has password "testpassword".
    correct_resp = auth_client.post(
        "/api/v1/users/change-password",
        json={"current_password": "testpassword", "new_password": "newtestpassword"},
    )
    assert correct_resp.status_code == 204, (
        f"Change password failed: {correct_resp.text}"
    )

    # Verify that login works with the new password.
    login_resp = auth_client.post(
        "/api/v1/auth/token",
        data={"username": "testuser", "password": "newtestpassword"},
    )
    assert login_resp.status_code == 200, "Login with new password failed"


def test_reset_user_password(superuser_client):
    """
    Test that a superuser can reset another user's password.
    """
    # Create a normal user for the reset.
    payload = {
        "username": "resetuser",
        "password": "oldpassword",
        "email": "resetuser@example.com",
        "full_name": "Reset User",
    }
    create_resp = superuser_client.post("/api/v1/users/", json=payload)
    assert create_resp.status_code == 200, f"User creation failed: {create_resp.text}"
    created_user = create_resp.json()
    user_id = created_user["id"]

    # Reset the user's password
    reset_resp = superuser_client.post(
        f"/api/v1/users/{user_id}/reset-password", json={"new_password": "newpassword"}
    )
    assert reset_resp.status_code == 200, f"Reset password failed: {reset_resp.text}"

    # Verify that login works with the new password
    login_resp = superuser_client.post(
        "/api/v1/auth/token",
        data={"username": payload["username"], "password": "newpassword"},
    )
    assert login_resp.status_code == 200, "Login with reset password failed"
