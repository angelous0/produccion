"""
Test Control de Producción endpoints:
- PUT /api/registros/{id}/control - Save fecha_entrega_esperada and responsable_actual
- GET /api/incidencias/{registro_id} - List incidencias
- POST /api/incidencias - Create incidencia
- PUT /api/incidencias/{id} - Resolve incidencia (estado: RESUELTA)
- GET /api/paralizaciones/{registro_id} - List paralizaciones
- POST /api/paralizaciones - Create paralización (only 1 active per registro)
- PUT /api/paralizaciones/{id}/levantar - Lift paralización
- GET /api/registros - Verify enriched fields

Logic tests:
- Estado operativo changes to PARALIZADA when there's an active paralización
- Estado operativo changes to EN_RIESGO when fecha_entrega_esperada has expired
- Estado operativo returns to NORMAL when paralización is lifted
"""

import pytest
import requests
import os
from datetime import date, timedelta
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://prod-cierre-flow.preview.emergentagent.com').rstrip('/')

# Test registro ID (corte 04)
TEST_REGISTRO_ID = "e7082b07-7a9b-4b45-af14-bde1ebc09238"


@pytest.fixture
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture
def auth_token(api_client):
    """Get authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "username": "eduard",
        "password": "eduard123"
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Authentication failed - skipping authenticated tests")


@pytest.fixture
def authenticated_client(api_client, auth_token):
    """Session with auth header"""
    api_client.headers.update({"Authorization": f"Bearer {auth_token}"})
    return api_client


class TestGetRegistrosEnrichedFields:
    """Test GET /api/registros returns new control fields"""
    
    def test_registros_returns_estado_operativo(self, api_client):
        """GET /api/registros should return estado_operativo field"""
        response = api_client.get(f"{BASE_URL}/api/registros")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        assert len(data) > 0, "Should have at least one registro"
        
        # Check first registro has required fields
        registro = data[0]
        assert "estado_operativo" in registro, "Should have estado_operativo field"
        assert "fecha_entrega_esperada" in registro, "Should have fecha_entrega_esperada field"
        assert "responsable_actual" in registro, "Should have responsable_actual field"
        assert "incidencias_abiertas" in registro, "Should have incidencias_abiertas field"
        assert "paralizacion_activa" in registro, "Should have paralizacion_activa field"
        print(f"✓ Registro {registro['n_corte']} has all control fields: estado_operativo={registro['estado_operativo']}")


class TestControlEndpoint:
    """Test PUT /api/registros/{id}/control endpoint"""
    
    def test_update_fecha_entrega(self, api_client):
        """Should update fecha_entrega_esperada"""
        future_date = (date.today() + timedelta(days=10)).isoformat()
        response = api_client.put(
            f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/control",
            json={"fecha_entrega_esperada": future_date}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "message" in data, "Should have message in response"
        assert "estado_operativo" in data, "Should return estado_operativo"
        print(f"✓ Updated fecha_entrega_esperada to {future_date}, estado_operativo={data['estado_operativo']}")
        
        # Verify it was persisted
        get_response = api_client.get(f"{BASE_URL}/api/registros")
        registros = get_response.json()
        registro = next((r for r in registros if r['id'] == TEST_REGISTRO_ID), None)
        assert registro is not None, "Registro should exist"
        assert registro['fecha_entrega_esperada'] == future_date, f"fecha should be {future_date}, got {registro['fecha_entrega_esperada']}"
    
    def test_update_responsable(self, api_client):
        """Should update responsable_actual"""
        response = api_client.put(
            f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/control",
            json={"responsable_actual": "Taller Externo TEST"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ Updated responsable_actual to 'Taller Externo TEST'")
        
        # Verify it was persisted
        get_response = api_client.get(f"{BASE_URL}/api/registros")
        registros = get_response.json()
        registro = next((r for r in registros if r['id'] == TEST_REGISTRO_ID), None)
        assert registro is not None, "Registro should exist"
        assert registro['responsable_actual'] == "Taller Externo TEST", f"responsable should be 'Taller Externo TEST', got {registro['responsable_actual']}"
    
    def test_update_control_nonexistent_registro(self, api_client):
        """Should return 404 for nonexistent registro"""
        response = api_client.put(
            f"{BASE_URL}/api/registros/nonexistent-id/control",
            json={"fecha_entrega_esperada": date.today().isoformat()}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Returns 404 for nonexistent registro")


class TestIncidenciasEndpoints:
    """Test incidencias CRUD endpoints"""
    
    def test_get_incidencias_empty(self, api_client):
        """GET /api/incidencias/{registro_id} should return list (may be empty)"""
        response = api_client.get(f"{BASE_URL}/api/incidencias/{TEST_REGISTRO_ID}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ GET /api/incidencias returned {len(data)} incidencias")
    
    def test_create_incidencia(self, api_client):
        """POST /api/incidencias should create new incidencia"""
        response = api_client.post(f"{BASE_URL}/api/incidencias", json={
            "registro_id": TEST_REGISTRO_ID,
            "tipo": "FALTA_MATERIAL",
            "comentario": "Test incidencia - falta material",
            "usuario": "test_user"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "id" in data, "Should have id in response"
        assert data["tipo"] == "FALTA_MATERIAL", "tipo should be FALTA_MATERIAL"
        assert data["estado"] == "ABIERTA", "estado should be ABIERTA"
        assert data["registro_id"] == TEST_REGISTRO_ID, "registro_id should match"
        print(f"✓ Created incidencia {data['id']} with tipo={data['tipo']}, estado={data['estado']}")
        return data["id"]
    
    def test_create_incidencia_all_tipos(self, api_client):
        """Should be able to create incidencias with all tipos"""
        tipos = ["FALTA_AVIOS", "RETRASO_TALLER", "CALIDAD", "CAMBIO_PRIORIDAD", "OTRO"]
        created_ids = []
        
        for tipo in tipos:
            response = api_client.post(f"{BASE_URL}/api/incidencias", json={
                "registro_id": TEST_REGISTRO_ID,
                "tipo": tipo,
                "comentario": f"Test incidencia {tipo}",
                "usuario": "test_user"
            })
            assert response.status_code == 200, f"Expected 200 for tipo {tipo}, got {response.status_code}"
            created_ids.append(response.json()["id"])
        
        print(f"✓ Created incidencias for all tipos: {tipos}")
        return created_ids
    
    def test_resolve_incidencia(self, api_client):
        """PUT /api/incidencias/{id} should resolve incidencia"""
        # First create an incidencia
        create_response = api_client.post(f"{BASE_URL}/api/incidencias", json={
            "registro_id": TEST_REGISTRO_ID,
            "tipo": "CALIDAD",
            "comentario": "Test incidencia to resolve",
            "usuario": "test_user"
        })
        assert create_response.status_code == 200
        inc_id = create_response.json()["id"]
        
        # Now resolve it
        resolve_response = api_client.put(f"{BASE_URL}/api/incidencias/{inc_id}", json={
            "estado": "RESUELTA"
        })
        assert resolve_response.status_code == 200, f"Expected 200, got {resolve_response.status_code}: {resolve_response.text}"
        
        data = resolve_response.json()
        assert data["estado"] == "RESUELTA", f"estado should be RESUELTA, got {data['estado']}"
        print(f"✓ Resolved incidencia {inc_id}, estado={data['estado']}")
    
    def test_incidencias_count_in_registros(self, api_client):
        """GET /api/registros should show incidencias_abiertas count"""
        response = api_client.get(f"{BASE_URL}/api/registros")
        assert response.status_code == 200
        
        registros = response.json()
        registro = next((r for r in registros if r['id'] == TEST_REGISTRO_ID), None)
        assert registro is not None
        
        count = registro['incidencias_abiertas']
        print(f"✓ Registro {registro['n_corte']} has {count} incidencias abiertas")
        
        # Verify with direct count
        inc_response = api_client.get(f"{BASE_URL}/api/incidencias/{TEST_REGISTRO_ID}")
        incidencias = inc_response.json()
        abiertas = [i for i in incidencias if i['estado'] == 'ABIERTA']
        assert count == len(abiertas), f"Count mismatch: registros={count}, actual={len(abiertas)}"
    
    def test_create_incidencia_nonexistent_registro(self, api_client):
        """Should return 404 for nonexistent registro"""
        response = api_client.post(f"{BASE_URL}/api/incidencias", json={
            "registro_id": "nonexistent-id",
            "tipo": "CALIDAD",
            "comentario": "Test",
            "usuario": "test"
        })
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Returns 404 for nonexistent registro")


class TestParalizacionesEndpoints:
    """Test paralizaciones CRUD endpoints"""
    
    def test_get_paralizaciones(self, api_client):
        """GET /api/paralizaciones/{registro_id} should return list"""
        response = api_client.get(f"{BASE_URL}/api/paralizaciones/{TEST_REGISTRO_ID}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ GET /api/paralizaciones returned {len(data)} paralizaciones")
    
    def test_create_paralizacion_and_verify_estado(self, api_client):
        """POST /api/paralizaciones should create and change estado_operativo to PARALIZADA"""
        # First check there's no active paralizacion
        get_par = api_client.get(f"{BASE_URL}/api/paralizaciones/{TEST_REGISTRO_ID}")
        existing = [p for p in get_par.json() if p.get('activa')]
        
        if existing:
            # Levantar existing paralizacion first
            for p in existing:
                api_client.put(f"{BASE_URL}/api/paralizaciones/{p['id']}/levantar")
        
        # Create paralización
        response = api_client.post(f"{BASE_URL}/api/paralizaciones", json={
            "registro_id": TEST_REGISTRO_ID,
            "motivo": "FALTA_MATERIAL",
            "comentario": "Test paralización"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "id" in data, "Should have id in response"
        assert data["activa"] == True, "activa should be True"
        assert data["motivo"] == "FALTA_MATERIAL", "motivo should match"
        par_id = data["id"]
        print(f"✓ Created paralización {par_id}, activa={data['activa']}")
        
        # Verify estado_operativo changed to PARALIZADA
        reg_response = api_client.get(f"{BASE_URL}/api/registros")
        registro = next((r for r in reg_response.json() if r['id'] == TEST_REGISTRO_ID), None)
        assert registro['estado_operativo'] == 'PARALIZADA', f"Expected PARALIZADA, got {registro['estado_operativo']}"
        assert registro['paralizacion_activa'] is not None, "Should have paralizacion_activa"
        print(f"✓ Estado operativo changed to PARALIZADA")
        
        return par_id
    
    def test_only_one_active_paralizacion(self, api_client):
        """Should not allow creating second active paralización"""
        # Ensure there's an active paralizacion
        get_par = api_client.get(f"{BASE_URL}/api/paralizaciones/{TEST_REGISTRO_ID}")
        existing_active = [p for p in get_par.json() if p.get('activa')]
        
        if not existing_active:
            # Create one first
            api_client.post(f"{BASE_URL}/api/paralizaciones", json={
                "registro_id": TEST_REGISTRO_ID,
                "motivo": "CALIDAD",
                "comentario": "First paralización"
            })
        
        # Try to create another - should fail
        response = api_client.post(f"{BASE_URL}/api/paralizaciones", json={
            "registro_id": TEST_REGISTRO_ID,
            "motivo": "TALLER",
            "comentario": "Second paralización - should fail"
        })
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "Ya existe una paralización activa" in response.json().get('detail', ''), "Should indicate active paralizacion exists"
        print("✓ Cannot create second active paralización - returns 400")
    
    def test_levantar_paralizacion_and_verify_estado(self, api_client):
        """PUT /api/paralizaciones/{id}/levantar should lift and change estado_operativo"""
        # Ensure there's an active paralizacion
        get_par = api_client.get(f"{BASE_URL}/api/paralizaciones/{TEST_REGISTRO_ID}")
        existing_active = [p for p in get_par.json() if p.get('activa')]
        
        if not existing_active:
            # Create one first
            create_resp = api_client.post(f"{BASE_URL}/api/paralizaciones", json={
                "registro_id": TEST_REGISTRO_ID,
                "motivo": "CALIDAD",
                "comentario": "Paralización to lift"
            })
            par_id = create_resp.json()['id']
        else:
            par_id = existing_active[0]['id']
        
        # Levantar
        response = api_client.put(f"{BASE_URL}/api/paralizaciones/{par_id}/levantar")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["activa"] == False, f"activa should be False, got {data['activa']}"
        assert data.get("fecha_fin") is not None, "Should have fecha_fin"
        print(f"✓ Levantada paralización {par_id}, activa={data['activa']}")
        
        # Verify estado_operativo changed back (should be NORMAL or EN_RIESGO based on fecha)
        reg_response = api_client.get(f"{BASE_URL}/api/registros")
        registro = next((r for r in reg_response.json() if r['id'] == TEST_REGISTRO_ID), None)
        assert registro['estado_operativo'] != 'PARALIZADA', f"Should not be PARALIZADA after levantar"
        assert registro['paralizacion_activa'] is None, "Should not have paralizacion_activa"
        print(f"✓ Estado operativo returned to {registro['estado_operativo']}")
    
    def test_levantar_already_lifted(self, api_client):
        """Should return 400 when trying to lift already lifted paralización"""
        # Get a lifted paralizacion
        get_par = api_client.get(f"{BASE_URL}/api/paralizaciones/{TEST_REGISTRO_ID}")
        lifted = [p for p in get_par.json() if not p.get('activa')]
        
        if lifted:
            par_id = lifted[0]['id']
            response = api_client.put(f"{BASE_URL}/api/paralizaciones/{par_id}/levantar")
            assert response.status_code == 400, f"Expected 400, got {response.status_code}"
            print("✓ Cannot levantar already lifted paralización - returns 400")
        else:
            pytest.skip("No lifted paralizaciones to test")
    
    def test_create_paralizacion_nonexistent_registro(self, api_client):
        """Should return 404 for nonexistent registro"""
        response = api_client.post(f"{BASE_URL}/api/paralizaciones", json={
            "registro_id": "nonexistent-id",
            "motivo": "CALIDAD",
            "comentario": "Test"
        })
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Returns 404 for nonexistent registro")


class TestEstadoOperativoLogic:
    """Test estado_operativo automatic calculation logic"""
    
    def test_estado_en_riesgo_when_fecha_expired(self, api_client):
        """Estado should be EN_RIESGO when fecha_entrega_esperada is in the past"""
        # First ensure no active paralizacion
        get_par = api_client.get(f"{BASE_URL}/api/paralizaciones/{TEST_REGISTRO_ID}")
        for p in get_par.json():
            if p.get('activa'):
                api_client.put(f"{BASE_URL}/api/paralizaciones/{p['id']}/levantar")
        
        # Set fecha_entrega_esperada to yesterday
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        response = api_client.put(
            f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/control",
            json={"fecha_entrega_esperada": yesterday}
        )
        assert response.status_code == 200
        
        # Check estado_operativo
        data = response.json()
        assert data['estado_operativo'] == 'EN_RIESGO', f"Expected EN_RIESGO, got {data['estado_operativo']}"
        print(f"✓ Estado operativo is EN_RIESGO when fecha expired ({yesterday})")
    
    def test_estado_normal_when_fecha_future(self, api_client):
        """Estado should be NORMAL when fecha_entrega_esperada is in the future"""
        # First ensure no active paralizacion
        get_par = api_client.get(f"{BASE_URL}/api/paralizaciones/{TEST_REGISTRO_ID}")
        for p in get_par.json():
            if p.get('activa'):
                api_client.put(f"{BASE_URL}/api/paralizaciones/{p['id']}/levantar")
        
        # Set fecha_entrega_esperada to future
        future_date = (date.today() + timedelta(days=30)).isoformat()
        response = api_client.put(
            f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/control",
            json={"fecha_entrega_esperada": future_date}
        )
        assert response.status_code == 200
        
        # Check estado_operativo
        data = response.json()
        assert data['estado_operativo'] == 'NORMAL', f"Expected NORMAL, got {data['estado_operativo']}"
        print(f"✓ Estado operativo is NORMAL when fecha is in future ({future_date})")
    
    def test_estado_paralizada_overrides_en_riesgo(self, api_client):
        """PARALIZADA status should override EN_RIESGO"""
        # First ensure no active paralizacion
        get_par = api_client.get(f"{BASE_URL}/api/paralizaciones/{TEST_REGISTRO_ID}")
        for p in get_par.json():
            if p.get('activa'):
                api_client.put(f"{BASE_URL}/api/paralizaciones/{p['id']}/levantar")
        
        # Set fecha to past (would be EN_RIESGO)
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        api_client.put(
            f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/control",
            json={"fecha_entrega_esperada": yesterday}
        )
        
        # Create paralización
        response = api_client.post(f"{BASE_URL}/api/paralizaciones", json={
            "registro_id": TEST_REGISTRO_ID,
            "motivo": "FALTA_AVIOS",
            "comentario": "Test override"
        })
        assert response.status_code == 200
        par_id = response.json()['id']
        
        # Check estado_operativo is PARALIZADA, not EN_RIESGO
        reg_response = api_client.get(f"{BASE_URL}/api/registros")
        registro = next((r for r in reg_response.json() if r['id'] == TEST_REGISTRO_ID), None)
        assert registro['estado_operativo'] == 'PARALIZADA', f"Expected PARALIZADA, got {registro['estado_operativo']}"
        print("✓ PARALIZADA status overrides EN_RIESGO")
        
        # Cleanup - levantar
        api_client.put(f"{BASE_URL}/api/paralizaciones/{par_id}/levantar")


class TestCleanup:
    """Cleanup test data after tests"""
    
    def test_cleanup_test_data(self, api_client):
        """Clean up all test incidencias and paralizaciones, reset control fields"""
        # Levantar any active paralizaciones
        get_par = api_client.get(f"{BASE_URL}/api/paralizaciones/{TEST_REGISTRO_ID}")
        for p in get_par.json():
            if p.get('activa'):
                api_client.put(f"{BASE_URL}/api/paralizaciones/{p['id']}/levantar")
        
        # Delete test incidencias
        inc_response = api_client.get(f"{BASE_URL}/api/incidencias/{TEST_REGISTRO_ID}")
        for inc in inc_response.json():
            if "Test" in (inc.get('comentario') or '') or inc.get('usuario') == 'test_user':
                api_client.delete(f"{BASE_URL}/api/incidencias/{inc['id']}")
        
        # Reset control fields
        api_client.put(
            f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/control",
            json={
                "fecha_entrega_esperada": None,
                "responsable_actual": None
            }
        )
        print("✓ Cleanup completed")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
