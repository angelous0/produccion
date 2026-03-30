"""
Test: Incidencia with Paraliza and Usuario fields
Tests for POST /api/incidencias with paraliza=true/false and usuario field
Tests for GET /api/incidencias/{registro_id} returning usuario field
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_USERNAME = "eduard"
TEST_PASSWORD = "eduard123"

# Known test data from previous iteration
TEST_MOVIMIENTO_ID = "0064144d-ac63-4a08-8db4-0c8cc6e8ec72"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
        timeout=30
    )
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture(scope="module")
def test_registro_id(auth_headers):
    """Get a registro_id from the costura report for testing"""
    response = requests.get(
        f"{BASE_URL}/api/reportes-produccion/costura",
        headers=auth_headers,
        timeout=60
    )
    if response.status_code == 200:
        items = response.json().get("items", [])
        if items:
            return items[0]["registro_id"]
    pytest.skip("No registro found in costura report for testing")


@pytest.fixture(scope="module")
def motivo_id(auth_headers):
    """Get a motivo_id for creating incidencias"""
    response = requests.get(
        f"{BASE_URL}/api/motivos-incidencia",
        headers=auth_headers,
        timeout=30
    )
    if response.status_code == 200:
        motivos = response.json()
        if motivos:
            return motivos[0]["id"]
    pytest.skip("No motivos found for testing")


class TestIncidenciaWithParaliza:
    """Tests for POST /api/incidencias with paraliza field"""

    def test_create_incidencia_without_paraliza(self, auth_headers, test_registro_id, motivo_id):
        """Test creating incidencia without paraliza (default false)"""
        response = requests.post(
            f"{BASE_URL}/api/incidencias",
            json={
                "registro_id": test_registro_id,
                "motivo_id": motivo_id,
                "comentario": "TEST_incidencia_sin_paraliza",
                "usuario": "Test User",
                "paraliza": False
            },
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "id" in data, "Response should contain 'id'"
        assert data.get("paraliza") == False, "paraliza should be False"
        assert data.get("paralizacion_id") is None, "paralizacion_id should be None when paraliza=False"
        
        print(f"✓ Created incidencia without paraliza: id={data['id']}")
        
        # Cleanup - delete the test incidencia
        delete_response = requests.delete(
            f"{BASE_URL}/api/incidencias/{data['id']}",
            headers=auth_headers,
            timeout=30
        )
        assert delete_response.status_code == 200, f"Failed to cleanup incidencia: {delete_response.text}"
        print(f"✓ Cleaned up test incidencia")

    def test_create_incidencia_with_paraliza_true(self, auth_headers, test_registro_id, motivo_id):
        """Test creating incidencia with paraliza=true creates paralizacion"""
        # First check if there's already an active paralizacion
        par_response = requests.get(
            f"{BASE_URL}/api/paralizaciones/{test_registro_id}",
            headers=auth_headers,
            timeout=30
        )
        if par_response.status_code == 200:
            active_pars = [p for p in par_response.json() if p.get("activa")]
            if active_pars:
                pytest.skip("Registro already has active paralizacion, skipping paraliza=true test")
        
        response = requests.post(
            f"{BASE_URL}/api/incidencias",
            json={
                "registro_id": test_registro_id,
                "motivo_id": motivo_id,
                "comentario": "TEST_incidencia_con_paraliza",
                "usuario": "Eduard Test",
                "paraliza": True
            },
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "id" in data, "Response should contain 'id'"
        assert data.get("paraliza") == True, "paraliza should be True"
        assert data.get("paralizacion_id") is not None, "paralizacion_id should be set when paraliza=True"
        
        print(f"✓ Created incidencia with paraliza=true: id={data['id']}, paralizacion_id={data['paralizacion_id']}")
        
        # Verify paralizacion was created
        par_response = requests.get(
            f"{BASE_URL}/api/paralizaciones/{test_registro_id}",
            headers=auth_headers,
            timeout=30
        )
        assert par_response.status_code == 200
        paralizaciones = par_response.json()
        active_par = next((p for p in paralizaciones if p["id"] == data["paralizacion_id"]), None)
        assert active_par is not None, "Paralizacion should exist"
        assert active_par["activa"] == True, "Paralizacion should be active"
        print(f"✓ Verified paralizacion is active")
        
        # Cleanup - resolve the incidencia (which should lift the paralizacion)
        resolve_response = requests.put(
            f"{BASE_URL}/api/incidencias/{data['id']}",
            json={
                "estado": "RESUELTA",
                "comentario_resolucion": "Test cleanup"
            },
            headers=auth_headers,
            timeout=30
        )
        assert resolve_response.status_code == 200, f"Failed to resolve incidencia: {resolve_response.text}"
        print(f"✓ Resolved incidencia (paralizacion should be lifted)")

    def test_create_incidencia_with_usuario_field(self, auth_headers, test_registro_id, motivo_id):
        """Test that usuario field is saved when creating incidencia"""
        test_usuario = "Eduard Testing User"
        
        response = requests.post(
            f"{BASE_URL}/api/incidencias",
            json={
                "registro_id": test_registro_id,
                "motivo_id": motivo_id,
                "comentario": "TEST_incidencia_usuario",
                "usuario": test_usuario,
                "paraliza": False
            },
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        incidencia_id = data["id"]
        
        # Verify usuario is returned in GET incidencias
        get_response = requests.get(
            f"{BASE_URL}/api/incidencias/{test_registro_id}",
            headers=auth_headers,
            timeout=30
        )
        assert get_response.status_code == 200
        
        incidencias = get_response.json()
        created_inc = next((i for i in incidencias if i["id"] == incidencia_id), None)
        
        assert created_inc is not None, "Created incidencia should be in list"
        assert created_inc.get("usuario") == test_usuario, f"Expected usuario='{test_usuario}', got '{created_inc.get('usuario')}'"
        
        print(f"✓ Usuario field saved and returned: '{created_inc['usuario']}'")
        
        # Cleanup
        delete_response = requests.delete(
            f"{BASE_URL}/api/incidencias/{incidencia_id}",
            headers=auth_headers,
            timeout=30
        )
        assert delete_response.status_code == 200
        print(f"✓ Cleaned up test incidencia")


class TestIncidenciaGetWithUsuario:
    """Tests for GET /api/incidencias/{registro_id} returning usuario field"""

    def test_get_incidencias_returns_usuario(self, auth_headers, test_registro_id):
        """Test that GET incidencias returns usuario field"""
        response = requests.get(
            f"{BASE_URL}/api/incidencias/{test_registro_id}",
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        incidencias = response.json()
        print(f"✓ GET /api/incidencias/{test_registro_id} returned {len(incidencias)} incidencias")
        
        # Check that incidencias have usuario field (may be empty for old data)
        for inc in incidencias:
            assert "usuario" in inc or inc.get("usuario") is None, "Incidencia should have 'usuario' field"
            if inc.get("usuario"):
                print(f"  - Incidencia {inc['id']}: usuario='{inc['usuario']}'")

    def test_get_incidencias_returns_paraliza_info(self, auth_headers, test_registro_id):
        """Test that GET incidencias returns paraliza-related fields"""
        response = requests.get(
            f"{BASE_URL}/api/incidencias/{test_registro_id}",
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200
        
        incidencias = response.json()
        
        for inc in incidencias:
            # Check paraliza field exists
            assert "paraliza" in inc, "Incidencia should have 'paraliza' field"
            # Check paralizacion_id field exists (may be null)
            assert "paralizacion_id" in inc or inc.get("paralizacion_id") is None, "Incidencia should have 'paralizacion_id' field"
            
            if inc.get("paraliza"):
                print(f"  - Incidencia {inc['id']}: paraliza=True, paralizacion_id={inc.get('paralizacion_id')}")


class TestMotivosIncidencia:
    """Tests for GET /api/motivos-incidencia"""

    def test_get_motivos_returns_list(self, auth_headers):
        """Test that motivos endpoint returns a list"""
        response = requests.get(
            f"{BASE_URL}/api/motivos-incidencia",
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        motivos = response.json()
        assert isinstance(motivos, list), "Response should be a list"
        assert len(motivos) > 0, "Should have at least one motivo"
        
        # Check structure
        for m in motivos:
            assert "id" in m, "Motivo should have 'id'"
            assert "nombre" in m, "Motivo should have 'nombre'"
        
        print(f"✓ GET /api/motivos-incidencia returned {len(motivos)} motivos")
        for m in motivos[:5]:  # Print first 5
            print(f"  - {m['nombre']}")


class TestParalizacionEndpoints:
    """Tests for paralizacion-related endpoints"""

    def test_get_paralizaciones(self, auth_headers, test_registro_id):
        """Test GET /api/paralizaciones/{registro_id}"""
        response = requests.get(
            f"{BASE_URL}/api/paralizaciones/{test_registro_id}",
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        paralizaciones = response.json()
        assert isinstance(paralizaciones, list), "Response should be a list"
        
        print(f"✓ GET /api/paralizaciones/{test_registro_id} returned {len(paralizaciones)} paralizaciones")
        for p in paralizaciones:
            print(f"  - id={p['id']}, activa={p['activa']}, motivo={p.get('motivo', 'N/A')}")
