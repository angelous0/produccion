"""
Test suite for Trazabilidad Unificada module
- Fallados CRUD (create, read, update, delete)
- Arreglos CRUD (create, read, close, delete)
- Resumen de cantidades (balance del lote)
- Trazabilidad completa (timeline unificado)
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test registro ID with most data (Corte 01, 5 movimientos)
TEST_REGISTRO_ID = "c74d3460-3e8b-4d4c-88e5-06bff012d6f5"

# Test credentials
TEST_USERNAME = "eduard"
TEST_PASSWORD = "eduard123"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username": TEST_USERNAME,
        "password": TEST_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def api_client(auth_token):
    """Shared requests session with auth"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session


class TestFalladosCRUD:
    """Test CRUD operations for Fallados (defective products)"""
    
    created_fallado_id = None
    
    def test_get_fallados_empty_or_list(self, api_client):
        """GET /api/fallados - should return list (empty or with data)"""
        response = api_client.get(f"{BASE_URL}/api/fallados")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"GET /api/fallados: {len(data)} fallados found")
    
    def test_get_fallados_with_registro_filter(self, api_client):
        """GET /api/fallados?registro_id=... - filter by registro"""
        response = api_client.get(f"{BASE_URL}/api/fallados?registro_id={TEST_REGISTRO_ID}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        # All returned fallados should belong to the filtered registro
        for f in data:
            assert f.get("registro_id") == TEST_REGISTRO_ID, f"Fallado {f.get('id')} has wrong registro_id"
        print(f"GET /api/fallados?registro_id={TEST_REGISTRO_ID}: {len(data)} fallados")
    
    def test_create_fallado_success(self, api_client):
        """POST /api/fallados - create fallado with valid data"""
        payload = {
            "registro_id": TEST_REGISTRO_ID,
            "cantidad_detectada": 10,
            "cantidad_reparable": 7,
            "cantidad_no_reparable": 3,
            "destino_no_reparable": "LIQUIDACION",
            "motivo": "TEST - Costura defectuosa",
            "observaciones": "Creado por test automatizado"
        }
        response = api_client.post(f"{BASE_URL}/api/fallados", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "id" in data, "Response should contain 'id'"
        assert data.get("message") == "Fallado registrado", f"Unexpected message: {data.get('message')}"
        TestFalladosCRUD.created_fallado_id = data["id"]
        print(f"POST /api/fallados: Created fallado {data['id']}")
    
    def test_create_fallado_validation_error(self, api_client):
        """POST /api/fallados - validation: reparable + no_reparable > detectada"""
        payload = {
            "registro_id": TEST_REGISTRO_ID,
            "cantidad_detectada": 5,
            "cantidad_reparable": 4,
            "cantidad_no_reparable": 3,  # 4+3=7 > 5
            "motivo": "TEST - Should fail validation"
        }
        response = api_client.post(f"{BASE_URL}/api/fallados", json=payload)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        assert "exceder" in data.get("detail", "").lower() or "no puede" in data.get("detail", "").lower(), \
            f"Expected validation error about exceeding, got: {data.get('detail')}"
        print(f"POST /api/fallados validation: Correctly rejected - {data.get('detail')}")
    
    def test_get_created_fallado(self, api_client):
        """Verify created fallado appears in list"""
        if not TestFalladosCRUD.created_fallado_id:
            pytest.skip("No fallado was created")
        
        response = api_client.get(f"{BASE_URL}/api/fallados?registro_id={TEST_REGISTRO_ID}")
        assert response.status_code == 200
        data = response.json()
        
        found = any(f.get("id") == TestFalladosCRUD.created_fallado_id for f in data)
        assert found, f"Created fallado {TestFalladosCRUD.created_fallado_id} not found in list"
        print(f"GET /api/fallados: Verified fallado {TestFalladosCRUD.created_fallado_id} exists")
    
    def test_update_fallado(self, api_client):
        """PUT /api/fallados/{id} - update fallado"""
        if not TestFalladosCRUD.created_fallado_id:
            pytest.skip("No fallado was created")
        
        payload = {
            "motivo": "TEST - Motivo actualizado",
            "observaciones": "Actualizado por test"
        }
        response = api_client.put(
            f"{BASE_URL}/api/fallados/{TestFalladosCRUD.created_fallado_id}",
            json=payload
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("message") == "Fallado actualizado", f"Unexpected message: {data.get('message')}"
        print(f"PUT /api/fallados/{TestFalladosCRUD.created_fallado_id}: Updated successfully")
    
    def test_update_fallado_not_found(self, api_client):
        """PUT /api/fallados/{id} - 404 for non-existent fallado"""
        fake_id = str(uuid.uuid4())
        response = api_client.put(f"{BASE_URL}/api/fallados/{fake_id}", json={"motivo": "test"})
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print(f"PUT /api/fallados/{fake_id}: Correctly returned 404")


class TestArreglosCRUD:
    """Test CRUD operations for Arreglos (repairs)"""
    
    created_arreglo_id = None
    
    def test_get_arreglos_empty_or_list(self, api_client):
        """GET /api/arreglos - should return list"""
        response = api_client.get(f"{BASE_URL}/api/arreglos")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"GET /api/arreglos: {len(data)} arreglos found")
    
    def test_get_arreglos_with_registro_filter(self, api_client):
        """GET /api/arreglos?registro_id=... - filter by registro"""
        response = api_client.get(f"{BASE_URL}/api/arreglos?registro_id={TEST_REGISTRO_ID}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        for a in data:
            assert a.get("registro_id") == TEST_REGISTRO_ID, f"Arreglo {a.get('id')} has wrong registro_id"
        print(f"GET /api/arreglos?registro_id={TEST_REGISTRO_ID}: {len(data)} arreglos")
    
    def test_create_arreglo_success(self, api_client):
        """POST /api/arreglos - create arreglo linked to fallado"""
        if not TestFalladosCRUD.created_fallado_id:
            pytest.skip("No fallado was created to link arreglo")
        
        payload = {
            "fallado_id": TestFalladosCRUD.created_fallado_id,
            "registro_id": TEST_REGISTRO_ID,
            "cantidad_enviada": 5,
            "tipo": "ARREGLO_EXTERNO",
            "observaciones": "TEST - Arreglo creado por test"
        }
        response = api_client.post(f"{BASE_URL}/api/arreglos", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "id" in data, "Response should contain 'id'"
        assert "fecha_limite" in data, "Response should contain 'fecha_limite'"
        TestArreglosCRUD.created_arreglo_id = data["id"]
        print(f"POST /api/arreglos: Created arreglo {data['id']} with fecha_limite {data['fecha_limite']}")
    
    def test_create_arreglo_exceeds_reparables(self, api_client):
        """POST /api/arreglos - validation: cantidad_enviada > reparables"""
        if not TestFalladosCRUD.created_fallado_id:
            pytest.skip("No fallado was created")
        
        # The fallado has 7 reparables, we already sent 5, so sending 5 more should fail
        payload = {
            "fallado_id": TestFalladosCRUD.created_fallado_id,
            "registro_id": TEST_REGISTRO_ID,
            "cantidad_enviada": 5,  # 5 + 5 = 10 > 7 reparables
            "tipo": "ARREGLO_INTERNO"
        }
        response = api_client.post(f"{BASE_URL}/api/arreglos", json=payload)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        assert "excede" in data.get("detail", "").lower(), f"Expected validation error, got: {data.get('detail')}"
        print(f"POST /api/arreglos validation: Correctly rejected - {data.get('detail')}")
    
    def test_create_arreglo_fallado_not_found(self, api_client):
        """POST /api/arreglos - 404 for non-existent fallado"""
        fake_fallado_id = str(uuid.uuid4())
        payload = {
            "fallado_id": fake_fallado_id,
            "registro_id": TEST_REGISTRO_ID,
            "cantidad_enviada": 1,
            "tipo": "ARREGLO_INTERNO"
        }
        response = api_client.post(f"{BASE_URL}/api/arreglos", json=payload)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print(f"POST /api/arreglos: Correctly returned 404 for non-existent fallado")
    
    def test_cerrar_arreglo_success(self, api_client):
        """PUT /api/arreglos/{id}/cerrar - close arreglo with result"""
        if not TestArreglosCRUD.created_arreglo_id:
            pytest.skip("No arreglo was created")
        
        payload = {
            "cantidad_resuelta": 4,
            "cantidad_no_resuelta": 1,
            "resultado_final": "BUENO",
            "observaciones": "TEST - Cerrado por test"
        }
        response = api_client.put(
            f"{BASE_URL}/api/arreglos/{TestArreglosCRUD.created_arreglo_id}/cerrar",
            json=payload
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("message") == "Arreglo cerrado", f"Unexpected message: {data.get('message')}"
        print(f"PUT /api/arreglos/{TestArreglosCRUD.created_arreglo_id}/cerrar: Closed successfully")
    
    def test_cerrar_arreglo_validation_error(self, api_client):
        """PUT /api/arreglos/{id}/cerrar - validation: resuelta + no_resuelta > enviada"""
        # Create a new arreglo to test validation
        if not TestFalladosCRUD.created_fallado_id:
            pytest.skip("No fallado was created")
        
        # First create a new arreglo with remaining reparables (7 - 5 = 2)
        payload = {
            "fallado_id": TestFalladosCRUD.created_fallado_id,
            "registro_id": TEST_REGISTRO_ID,
            "cantidad_enviada": 2,
            "tipo": "ARREGLO_INTERNO"
        }
        create_response = api_client.post(f"{BASE_URL}/api/arreglos", json=payload)
        if create_response.status_code != 200:
            pytest.skip(f"Could not create arreglo for validation test: {create_response.text}")
        
        new_arreglo_id = create_response.json()["id"]
        
        # Try to close with invalid quantities
        close_payload = {
            "cantidad_resuelta": 2,
            "cantidad_no_resuelta": 2,  # 2+2=4 > 2 enviada
            "resultado_final": "BUENO"
        }
        response = api_client.put(f"{BASE_URL}/api/arreglos/{new_arreglo_id}/cerrar", json=close_payload)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        
        # Cleanup - delete the test arreglo
        api_client.delete(f"{BASE_URL}/api/arreglos/{new_arreglo_id}")
        print(f"PUT /api/arreglos/cerrar validation: Correctly rejected exceeding quantities")
    
    def test_cerrar_arreglo_not_found(self, api_client):
        """PUT /api/arreglos/{id}/cerrar - 404 for non-existent arreglo"""
        fake_id = str(uuid.uuid4())
        response = api_client.put(f"{BASE_URL}/api/arreglos/{fake_id}/cerrar", json={
            "cantidad_resuelta": 1,
            "cantidad_no_resuelta": 0,
            "resultado_final": "BUENO"
        })
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print(f"PUT /api/arreglos/{fake_id}/cerrar: Correctly returned 404")


class TestResumenCantidades:
    """Test resumen-cantidades endpoint (balance del lote)"""
    
    def test_resumen_cantidades_success(self, api_client):
        """GET /api/registros/{id}/resumen-cantidades - get balance"""
        response = api_client.get(f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/resumen-cantidades")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify required fields
        required_fields = [
            "registro_id", "n_corte", "estado", "cantidad_inicial",
            "extraviado_faltante", "fallados_detectados", "reparables",
            "no_reparables", "reparados_cerrados", "pendientes_arreglo",
            "liquidacion", "segunda", "descarte", "alertas"
        ]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        assert data["registro_id"] == TEST_REGISTRO_ID
        assert isinstance(data["cantidad_inicial"], int)
        assert isinstance(data["alertas"], list)
        
        print(f"GET /api/registros/{TEST_REGISTRO_ID}/resumen-cantidades:")
        print(f"  - Cantidad inicial: {data['cantidad_inicial']}")
        print(f"  - Fallados detectados: {data['fallados_detectados']}")
        print(f"  - Reparables: {data['reparables']}")
        print(f"  - No reparables: {data['no_reparables']}")
        print(f"  - Reparados cerrados: {data['reparados_cerrados']}")
        print(f"  - Alertas: {len(data['alertas'])}")
    
    def test_resumen_cantidades_not_found(self, api_client):
        """GET /api/registros/{id}/resumen-cantidades - 404 for non-existent registro"""
        fake_id = str(uuid.uuid4())
        response = api_client.get(f"{BASE_URL}/api/registros/{fake_id}/resumen-cantidades")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print(f"GET /api/registros/{fake_id}/resumen-cantidades: Correctly returned 404")


class TestTrazabilidadCompleta:
    """Test trazabilidad-completa endpoint (timeline unificado)"""
    
    def test_trazabilidad_completa_success(self, api_client):
        """GET /api/registros/{id}/trazabilidad-completa - get timeline"""
        response = api_client.get(f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/trazabilidad-completa")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify structure
        assert "registro" in data, "Response should contain 'registro'"
        assert "eventos" in data, "Response should contain 'eventos'"
        assert "total_eventos" in data, "Response should contain 'total_eventos'"
        
        assert isinstance(data["eventos"], list)
        assert data["total_eventos"] == len(data["eventos"])
        
        # Verify evento types
        valid_tipos = ["MOVIMIENTO", "MERMA", "FALLADO", "ARREGLO", "DIVISION"]
        for evento in data["eventos"]:
            assert "tipo_evento" in evento, "Each evento should have 'tipo_evento'"
            assert evento["tipo_evento"] in valid_tipos, f"Invalid tipo_evento: {evento['tipo_evento']}"
            assert "fecha" in evento, "Each evento should have 'fecha'"
        
        # Count by type
        tipo_counts = {}
        for e in data["eventos"]:
            t = e["tipo_evento"]
            tipo_counts[t] = tipo_counts.get(t, 0) + 1
        
        print(f"GET /api/registros/{TEST_REGISTRO_ID}/trazabilidad-completa:")
        print(f"  - Total eventos: {data['total_eventos']}")
        for tipo, count in tipo_counts.items():
            print(f"  - {tipo}: {count}")
    
    def test_trazabilidad_completa_not_found(self, api_client):
        """GET /api/registros/{id}/trazabilidad-completa - 404 for non-existent registro"""
        fake_id = str(uuid.uuid4())
        response = api_client.get(f"{BASE_URL}/api/registros/{fake_id}/trazabilidad-completa")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print(f"GET /api/registros/{fake_id}/trazabilidad-completa: Correctly returned 404")


class TestCleanup:
    """Cleanup test data"""
    
    def test_delete_arreglo(self, api_client):
        """DELETE /api/arreglos/{id} - delete test arreglo"""
        if not TestArreglosCRUD.created_arreglo_id:
            pytest.skip("No arreglo to delete")
        
        response = api_client.delete(f"{BASE_URL}/api/arreglos/{TestArreglosCRUD.created_arreglo_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"DELETE /api/arreglos/{TestArreglosCRUD.created_arreglo_id}: Deleted successfully")
    
    def test_delete_fallado(self, api_client):
        """DELETE /api/fallados/{id} - delete test fallado (cascades arreglos)"""
        if not TestFalladosCRUD.created_fallado_id:
            pytest.skip("No fallado to delete")
        
        response = api_client.delete(f"{BASE_URL}/api/fallados/{TestFalladosCRUD.created_fallado_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"DELETE /api/fallados/{TestFalladosCRUD.created_fallado_id}: Deleted successfully")
    
    def test_verify_cleanup(self, api_client):
        """Verify test data was cleaned up"""
        if TestFalladosCRUD.created_fallado_id:
            response = api_client.get(f"{BASE_URL}/api/fallados?registro_id={TEST_REGISTRO_ID}")
            data = response.json()
            found = any(f.get("id") == TestFalladosCRUD.created_fallado_id for f in data)
            assert not found, "Test fallado should have been deleted"
            print("Cleanup verified: Test fallado no longer exists")
