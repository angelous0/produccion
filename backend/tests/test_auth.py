"""
Authentication System Tests
Tests for login, /auth/me, and user management endpoints
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_USER = "eduard"
ADMIN_PASSWORD = "eduard123"

class TestAuthLogin:
    """Tests for POST /api/auth/login"""
    
    def test_login_success(self):
        """Test successful login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": ADMIN_USER,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "access_token" in data, "Response should contain access_token"
        assert "token_type" in data, "Response should contain token_type"
        assert data["token_type"] == "bearer", "Token type should be bearer"
        assert "user" in data, "Response should contain user object"
        
        user = data["user"]
        assert user["username"] == ADMIN_USER, f"Username should be {ADMIN_USER}"
        assert user["rol"] == "admin", "User role should be admin"
        assert user["activo"] == True, "User should be active"
        assert "password_hash" not in user, "Password hash should not be exposed"
    
    def test_login_invalid_username(self):
        """Test login with invalid username"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "nonexistent_user",
            "password": "anypassword"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        
        data = response.json()
        assert "detail" in data, "Response should contain error detail"
    
    def test_login_invalid_password(self):
        """Test login with invalid password"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": ADMIN_USER,
            "password": "wrongpassword"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    def test_login_empty_credentials(self):
        """Test login with empty credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "",
            "password": ""
        })
        assert response.status_code in [401, 422], f"Expected 401 or 422, got {response.status_code}"


class TestAuthMe:
    """Tests for GET /api/auth/me"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": ADMIN_USER,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, "Login should succeed"
        return response.json()["access_token"]
    
    def test_get_me_authenticated(self, auth_token):
        """Test GET /api/auth/me with valid token"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        user = response.json()
        assert user["username"] == ADMIN_USER, f"Username should be {ADMIN_USER}"
        assert user["rol"] == "admin", "User role should be admin"
        assert "password_hash" not in user, "Password hash should not be exposed"
        assert "permisos" in user, "User should have permisos field"
    
    def test_get_me_no_token(self):
        """Test GET /api/auth/me without token"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    def test_get_me_invalid_token(self):
        """Test GET /api/auth/me with invalid token"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": "Bearer invalid_token_here"}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"


class TestUsuariosEndpoints:
    """Tests for /api/usuarios endpoints (admin only)"""
    
    @pytest.fixture
    def auth_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": ADMIN_USER,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, "Login should succeed"
        return response.json()["access_token"]
    
    @pytest.fixture
    def auth_headers(self, auth_token):
        """Get headers with auth token"""
        return {"Authorization": f"Bearer {auth_token}"}
    
    def test_get_usuarios_as_admin(self, auth_headers):
        """Test GET /api/usuarios as admin"""
        response = requests.get(f"{BASE_URL}/api/usuarios", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        users = response.json()
        assert isinstance(users, list), "Response should be a list"
        assert len(users) >= 1, "Should have at least one user (admin)"
        
        # Verify admin user is in the list
        admin_user = next((u for u in users if u["username"] == ADMIN_USER), None)
        assert admin_user is not None, f"Admin user {ADMIN_USER} should be in the list"
        assert "password_hash" not in admin_user, "Password hash should not be exposed"
    
    def test_get_usuarios_without_auth(self):
        """Test GET /api/usuarios without authentication"""
        response = requests.get(f"{BASE_URL}/api/usuarios")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    def test_create_usuario(self, auth_headers):
        """Test POST /api/usuarios - create new user"""
        test_username = f"TEST_user_{uuid.uuid4().hex[:8]}"
        
        response = requests.post(f"{BASE_URL}/api/usuarios", headers=auth_headers, json={
            "username": test_username,
            "password": "testpass123",
            "nombre_completo": "Test User",
            "email": f"{test_username}@test.com",
            "rol": "usuario",
            "permisos": {}
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "id" in data, "Response should contain user id"
        assert data["username"] == test_username, "Username should match"
        
        # Cleanup - delete the test user
        user_id = data["id"]
        delete_response = requests.delete(f"{BASE_URL}/api/usuarios/{user_id}", headers=auth_headers)
        assert delete_response.status_code == 200, "Cleanup should succeed"
    
    def test_create_usuario_duplicate_username(self, auth_headers):
        """Test POST /api/usuarios with duplicate username"""
        response = requests.post(f"{BASE_URL}/api/usuarios", headers=auth_headers, json={
            "username": ADMIN_USER,  # Already exists
            "password": "testpass123",
            "rol": "usuario"
        })
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        
        data = response.json()
        assert "detail" in data, "Response should contain error detail"
    
    def test_update_usuario(self, auth_headers):
        """Test PUT /api/usuarios/{id} - update user"""
        # First create a test user
        test_username = f"TEST_update_{uuid.uuid4().hex[:8]}"
        create_response = requests.post(f"{BASE_URL}/api/usuarios", headers=auth_headers, json={
            "username": test_username,
            "password": "testpass123",
            "rol": "usuario"
        })
        assert create_response.status_code == 200, "Create should succeed"
        user_id = create_response.json()["id"]
        
        # Update the user
        update_response = requests.put(f"{BASE_URL}/api/usuarios/{user_id}", headers=auth_headers, json={
            "nombre_completo": "Updated Name",
            "rol": "lectura"
        })
        assert update_response.status_code == 200, f"Expected 200, got {update_response.status_code}: {update_response.text}"
        
        # Verify update by getting users list
        list_response = requests.get(f"{BASE_URL}/api/usuarios", headers=auth_headers)
        users = list_response.json()
        updated_user = next((u for u in users if u["id"] == user_id), None)
        assert updated_user is not None, "Updated user should exist"
        assert updated_user["nombre_completo"] == "Updated Name", "Name should be updated"
        assert updated_user["rol"] == "lectura", "Role should be updated"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/usuarios/{user_id}", headers=auth_headers)
    
    def test_delete_usuario(self, auth_headers):
        """Test DELETE /api/usuarios/{id}"""
        # Create a test user
        test_username = f"TEST_delete_{uuid.uuid4().hex[:8]}"
        create_response = requests.post(f"{BASE_URL}/api/usuarios", headers=auth_headers, json={
            "username": test_username,
            "password": "testpass123",
            "rol": "usuario"
        })
        assert create_response.status_code == 200, "Create should succeed"
        user_id = create_response.json()["id"]
        
        # Delete the user
        delete_response = requests.delete(f"{BASE_URL}/api/usuarios/{user_id}", headers=auth_headers)
        assert delete_response.status_code == 200, f"Expected 200, got {delete_response.status_code}"
        
        # Verify deletion
        list_response = requests.get(f"{BASE_URL}/api/usuarios", headers=auth_headers)
        users = list_response.json()
        deleted_user = next((u for u in users if u["id"] == user_id), None)
        assert deleted_user is None, "Deleted user should not exist"
    
    def test_reset_password(self, auth_headers):
        """Test PUT /api/usuarios/{id}/reset-password"""
        # Create a test user
        test_username = f"TEST_reset_{uuid.uuid4().hex[:8]}"
        create_response = requests.post(f"{BASE_URL}/api/usuarios", headers=auth_headers, json={
            "username": test_username,
            "password": "testpass123",
            "rol": "usuario"
        })
        assert create_response.status_code == 200, "Create should succeed"
        user_id = create_response.json()["id"]
        
        # Reset password
        reset_response = requests.put(f"{BASE_URL}/api/usuarios/{user_id}/reset-password", headers=auth_headers)
        assert reset_response.status_code == 200, f"Expected 200, got {reset_response.status_code}"
        
        data = reset_response.json()
        assert "message" in data, "Response should contain message"
        # New password should be username + "123"
        expected_password = test_username + "123"
        assert expected_password in data["message"], f"Message should contain new password: {expected_password}"
        
        # Verify new password works
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": test_username,
            "password": expected_password
        })
        assert login_response.status_code == 200, "Login with new password should succeed"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/usuarios/{user_id}", headers=auth_headers)


class TestPermisosEstructura:
    """Tests for GET /api/permisos/estructura"""
    
    def test_get_estructura_permisos(self):
        """Test GET /api/permisos/estructura returns permission structure"""
        response = requests.get(f"{BASE_URL}/api/permisos/estructura")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "categorias" in data, "Response should contain categorias"
        assert isinstance(data["categorias"], list), "Categorias should be a list"
        assert len(data["categorias"]) > 0, "Should have at least one category"
        
        # Verify structure of first category
        first_cat = data["categorias"][0]
        assert "nombre" in first_cat, "Category should have nombre"
        assert "tablas" in first_cat, "Category should have tablas"
        
        # Verify structure of first table
        if first_cat["tablas"]:
            first_table = first_cat["tablas"][0]
            assert "key" in first_table, "Table should have key"
            assert "nombre" in first_table, "Table should have nombre"
            assert "acciones" in first_table, "Table should have acciones"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
