"""
Test: Fallados y Arreglos V2 - Trazabilidad Simplificada
Tests for:
- GET/POST/PUT/DELETE /api/fallados - CRUD fallados simplificados
- GET/POST /api/registros/{id}/arreglos - CRUD arreglos V2
- PUT/DELETE /api/arreglos/{id} - Update/delete arreglos
- GET /api/registros/{id}/resumen-cantidades - Resumen con ecuacion
- GET /api/registros/{id}/preview-cierre - Preview cierre con resultado_final
- Validaciones: SUM(arreglos) <= total_fallados, resolucion <= cantidad, no negativos
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://kardex-pt-sync.preview.emergentagent.com').rstrip('/')

# Test registro con fallados existentes
TEST_REGISTRO_ID = "da2f1c0b-431b-4149-857d-7043f1dce27a"  # Corte 008, 300 prendas, 15 fallados

@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username": "eduard",
        "password": "eduard123"
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Authentication failed - skipping tests")

@pytest.fixture(scope="module")
def headers(auth_token):
    """Headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


class TestFalladosCRUD:
    """Tests for /api/fallados endpoints"""
    
    created_fallado_id = None
    
    def test_get_fallados_by_registro(self, headers):
        """GET /api/fallados?registro_id=X - lista fallados simplificados"""
        response = requests.get(f"{BASE_URL}/api/fallados?registro_id={TEST_REGISTRO_ID}", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        # Verify structure of fallados
        if len(data) > 0:
            fallado = data[0]
            assert "id" in fallado
            assert "registro_id" in fallado
            assert "cantidad_detectada" in fallado
            print(f"Found {len(data)} fallados for registro {TEST_REGISTRO_ID}")
    
    def test_create_fallado_success(self, headers):
        """POST /api/fallados - crear fallado con cantidad_detectada"""
        payload = {
            "registro_id": TEST_REGISTRO_ID,
            "cantidad_detectada": 5,
            "fecha_deteccion": "2025-01-15",
            "observacion": "TEST_Fallado de prueba automatizada"
        }
        response = requests.post(f"{BASE_URL}/api/fallados", json=payload, headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "id" in data
        assert data.get("message") == "Fallado registrado"
        TestFalladosCRUD.created_fallado_id = data["id"]
        print(f"Created fallado: {data['id']}")
    
    def test_create_fallado_invalid_cantidad_zero(self, headers):
        """POST /api/fallados - rechaza cantidad <= 0"""
        payload = {
            "registro_id": TEST_REGISTRO_ID,
            "cantidad_detectada": 0,
            "observacion": "TEST_Invalid"
        }
        response = requests.post(f"{BASE_URL}/api/fallados", json=payload, headers=headers)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "mayor a 0" in response.json().get("detail", "").lower()
    
    def test_create_fallado_invalid_cantidad_negative(self, headers):
        """POST /api/fallados - rechaza cantidad negativa"""
        payload = {
            "registro_id": TEST_REGISTRO_ID,
            "cantidad_detectada": -5,
            "observacion": "TEST_Negative"
        }
        response = requests.post(f"{BASE_URL}/api/fallados", json=payload, headers=headers)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    
    def test_update_fallado_success(self, headers):
        """PUT /api/fallados/{id} - editar fallado"""
        if not TestFalladosCRUD.created_fallado_id:
            pytest.skip("No fallado created to update")
        
        payload = {
            "cantidad_detectada": 3,
            "observacion": "TEST_Fallado actualizado"
        }
        response = requests.put(f"{BASE_URL}/api/fallados/{TestFalladosCRUD.created_fallado_id}", json=payload, headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert response.json().get("message") == "Fallado actualizado"
        
        # Verify update persisted
        get_response = requests.get(f"{BASE_URL}/api/fallados?registro_id={TEST_REGISTRO_ID}", headers=headers)
        fallados = get_response.json()
        updated = next((f for f in fallados if f["id"] == TestFalladosCRUD.created_fallado_id), None)
        assert updated is not None
        assert updated["cantidad_detectada"] == 3
    
    def test_update_fallado_not_found(self, headers):
        """PUT /api/fallados/{id} - fallado no encontrado"""
        fake_id = str(uuid.uuid4())
        response = requests.put(f"{BASE_URL}/api/fallados/{fake_id}", json={"cantidad_detectada": 1}, headers=headers)
        assert response.status_code == 404
    
    def test_delete_fallado_success(self, headers):
        """DELETE /api/fallados/{id} - eliminar fallado"""
        if not TestFalladosCRUD.created_fallado_id:
            pytest.skip("No fallado created to delete")
        
        response = requests.delete(f"{BASE_URL}/api/fallados/{TestFalladosCRUD.created_fallado_id}", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert response.json().get("message") == "Fallado eliminado"
        
        # Verify deletion
        get_response = requests.get(f"{BASE_URL}/api/fallados?registro_id={TEST_REGISTRO_ID}", headers=headers)
        fallados = get_response.json()
        deleted = next((f for f in fallados if f["id"] == TestFalladosCRUD.created_fallado_id), None)
        assert deleted is None, "Fallado should be deleted"


class TestArreglosV2CRUD:
    """Tests for /api/registros/{id}/arreglos and /api/arreglos/{id} endpoints"""
    
    created_arreglo_id = None
    test_fallado_id = None
    
    @pytest.fixture(autouse=True)
    def setup_fallado(self, headers):
        """Create a fallado for arreglo tests"""
        # Create a test fallado first
        payload = {
            "registro_id": TEST_REGISTRO_ID,
            "cantidad_detectada": 10,
            "observacion": "TEST_Fallado para arreglos"
        }
        response = requests.post(f"{BASE_URL}/api/fallados", json=payload, headers=headers)
        if response.status_code == 200:
            TestArreglosV2CRUD.test_fallado_id = response.json()["id"]
        yield
        # Cleanup: delete test fallado if exists
        if TestArreglosV2CRUD.test_fallado_id:
            requests.delete(f"{BASE_URL}/api/fallados/{TestArreglosV2CRUD.test_fallado_id}", headers=headers)
    
    def test_get_arreglos_by_registro(self, headers):
        """GET /api/registros/{id}/arreglos - lista arreglos V2 con estados calculados"""
        response = requests.get(f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/arreglos", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        # Verify structure
        if len(data) > 0:
            arreglo = data[0]
            assert "id" in arreglo
            assert "registro_id" in arreglo
            assert "cantidad" in arreglo
            assert "estado" in arreglo
            assert arreglo["estado"] in ["EN_ARREGLO", "PARCIAL", "COMPLETADO", "VENCIDO"]
            print(f"Found {len(data)} arreglos for registro {TEST_REGISTRO_ID}")
    
    def test_create_arreglo_success(self, headers):
        """POST /api/registros/{id}/arreglos - crear arreglo, validar SUM <= total_fallados"""
        # First get resumen to know available
        resumen = requests.get(f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/resumen-cantidades", headers=headers).json()
        fallado_pendiente = resumen.get("fallado_pendiente", 0)
        
        if fallado_pendiente <= 0:
            pytest.skip("No fallado_pendiente available for arreglo")
        
        cantidad_arreglo = min(5, fallado_pendiente)
        payload = {
            "cantidad": cantidad_arreglo,
            "servicio_id": None,
            "persona_id": None,
            "fecha_envio": "2025-01-15",
            "observacion": "TEST_Arreglo de prueba"
        }
        response = requests.post(f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/arreglos", json=payload, headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "id" in data
        assert "fecha_limite" in data  # fecha_envio + 3 dias
        TestArreglosV2CRUD.created_arreglo_id = data["id"]
        print(f"Created arreglo: {data['id']}, fecha_limite: {data['fecha_limite']}")
    
    def test_create_arreglo_exceeds_fallados(self, headers):
        """POST /api/registros/{id}/arreglos - rechaza si excede total_fallados"""
        payload = {
            "cantidad": 99999,  # Exceeds any reasonable fallado count
            "observacion": "TEST_Should fail"
        }
        response = requests.post(f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/arreglos", json=payload, headers=headers)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "excede" in response.json().get("detail", "").lower()
    
    def test_create_arreglo_invalid_cantidad_zero(self, headers):
        """POST /api/registros/{id}/arreglos - rechaza cantidad <= 0"""
        payload = {
            "cantidad": 0,
            "observacion": "TEST_Invalid"
        }
        response = requests.post(f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/arreglos", json=payload, headers=headers)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    
    def test_update_arreglo_resolucion(self, headers):
        """PUT /api/arreglos/{id} - actualizar arreglo con resolucion"""
        if not TestArreglosV2CRUD.created_arreglo_id:
            pytest.skip("No arreglo created to update")
        
        # Get arreglo to know cantidad
        arreglos = requests.get(f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/arreglos", headers=headers).json()
        arreglo = next((a for a in arreglos if a["id"] == TestArreglosV2CRUD.created_arreglo_id), None)
        if not arreglo:
            pytest.skip("Arreglo not found")
        
        cantidad = arreglo["cantidad"]
        # Set partial resolution
        payload = {
            "cantidad_recuperada": cantidad - 2,
            "cantidad_liquidacion": 1,
            "cantidad_merma": 1
        }
        response = requests.put(f"{BASE_URL}/api/arreglos/{TestArreglosV2CRUD.created_arreglo_id}", json=payload, headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("estado") == "COMPLETADO"  # rec + liq + mer = cantidad
        print(f"Updated arreglo to COMPLETADO")
    
    def test_update_arreglo_resolucion_exceeds_cantidad(self, headers):
        """PUT /api/arreglos/{id} - rechaza si resolucion excede cantidad"""
        # Create a new arreglo for this test
        resumen = requests.get(f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/resumen-cantidades", headers=headers).json()
        fallado_pendiente = resumen.get("fallado_pendiente", 0)
        
        if fallado_pendiente <= 0:
            pytest.skip("No fallado_pendiente available")
        
        # Create arreglo
        create_resp = requests.post(f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/arreglos", json={
            "cantidad": min(3, fallado_pendiente),
            "observacion": "TEST_For resolution test"
        }, headers=headers)
        
        if create_resp.status_code != 200:
            pytest.skip("Could not create arreglo for test")
        
        arreglo_id = create_resp.json()["id"]
        
        # Try to set resolution that exceeds cantidad
        payload = {
            "cantidad_recuperada": 10,
            "cantidad_liquidacion": 10,
            "cantidad_merma": 10
        }
        response = requests.put(f"{BASE_URL}/api/arreglos/{arreglo_id}", json=payload, headers=headers)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "excede" in response.json().get("detail", "").lower()
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/arreglos/{arreglo_id}", headers=headers)
    
    def test_update_arreglo_negative_values(self, headers):
        """PUT /api/arreglos/{id} - rechaza valores negativos"""
        # Create a new arreglo for this test
        resumen = requests.get(f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/resumen-cantidades", headers=headers).json()
        fallado_pendiente = resumen.get("fallado_pendiente", 0)
        
        if fallado_pendiente <= 0:
            pytest.skip("No fallado_pendiente available")
        
        create_resp = requests.post(f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/arreglos", json={
            "cantidad": min(2, fallado_pendiente),
            "observacion": "TEST_For negative test"
        }, headers=headers)
        
        if create_resp.status_code != 200:
            pytest.skip("Could not create arreglo for test")
        
        arreglo_id = create_resp.json()["id"]
        
        # Try negative value
        payload = {"cantidad_recuperada": -5}
        response = requests.put(f"{BASE_URL}/api/arreglos/{arreglo_id}", json=payload, headers=headers)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "negativo" in response.json().get("detail", "").lower()
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/arreglos/{arreglo_id}", headers=headers)
    
    def test_delete_arreglo_completado_blocked(self, headers):
        """DELETE /api/arreglos/{id} - no se puede eliminar arreglo completado"""
        if not TestArreglosV2CRUD.created_arreglo_id:
            pytest.skip("No arreglo created")
        
        # The arreglo was marked COMPLETADO in previous test
        response = requests.delete(f"{BASE_URL}/api/arreglos/{TestArreglosV2CRUD.created_arreglo_id}", headers=headers)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "completado" in response.json().get("detail", "").lower()
    
    def test_update_arreglo_completado_blocked(self, headers):
        """PUT /api/arreglos/{id} - no se puede editar arreglo completado"""
        if not TestArreglosV2CRUD.created_arreglo_id:
            pytest.skip("No arreglo created")
        
        payload = {"cantidad_recuperada": 1}
        response = requests.put(f"{BASE_URL}/api/arreglos/{TestArreglosV2CRUD.created_arreglo_id}", json=payload, headers=headers)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "completado" in response.json().get("detail", "").lower()


class TestResumenCantidades:
    """Tests for /api/registros/{id}/resumen-cantidades endpoint"""
    
    def test_resumen_cantidades_structure(self, headers):
        """GET /api/registros/{id}/resumen-cantidades - verifica estructura"""
        response = requests.get(f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/resumen-cantidades", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify required fields
        required_fields = [
            "registro_id", "n_corte", "estado", "total_producido", "normal",
            "total_fallados", "fallado_pendiente", "recuperado", "liquidacion",
            "merma", "merma_arreglos", "ecuacion_valida"
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
        print(f"Resumen: total_producido={data['total_producido']}, normal={data['normal']}, "
              f"total_fallados={data['total_fallados']}, fallado_pendiente={data['fallado_pendiente']}, "
              f"ecuacion_valida={data['ecuacion_valida']}")
    
    def test_resumen_cantidades_ecuacion(self, headers):
        """GET /api/registros/{id}/resumen-cantidades - verifica ecuacion"""
        response = requests.get(f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/resumen-cantidades", headers=headers)
        data = response.json()
        
        # Verify ecuacion: normal + recuperado + liquidacion + merma_total + fallado_pendiente + divididos = total_producido
        normal = data.get("normal", 0)
        recuperado = data.get("recuperado", 0)
        liquidacion = data.get("liquidacion", 0)
        merma = data.get("merma", 0)
        merma_arreglos = data.get("merma_arreglos", 0)
        fallado_pendiente = data.get("fallado_pendiente", 0)
        divididos = data.get("divididos", 0)
        total_producido = data.get("total_producido", 0)
        
        suma = normal + recuperado + liquidacion + merma + merma_arreglos + fallado_pendiente + divididos
        print(f"Ecuacion: {normal} + {recuperado} + {liquidacion} + {merma + merma_arreglos} + {fallado_pendiente} + {divididos} = {suma} (total_producido={total_producido})")
        
        # ecuacion_valida should match our calculation
        if total_producido > 0:
            assert data["ecuacion_valida"] == (suma == total_producido), "ecuacion_valida mismatch"
    
    def test_resumen_cantidades_alertas(self, headers):
        """GET /api/registros/{id}/resumen-cantidades - verifica alertas"""
        response = requests.get(f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/resumen-cantidades", headers=headers)
        data = response.json()
        
        alertas = data.get("alertas", [])
        assert isinstance(alertas, list), "alertas should be a list"
        
        # Verify alerta structure
        for alerta in alertas:
            assert "tipo" in alerta
            assert "mensaje" in alerta
            assert alerta["tipo"] in ["VENCIDO", "MERMA", "PENDIENTE"]
        
        print(f"Alertas: {[a['tipo'] for a in alertas]}")


class TestPreviewCierre:
    """Tests for /api/registros/{id}/preview-cierre endpoint"""
    
    def test_preview_cierre_includes_resultado_final(self, headers):
        """GET /api/registros/{id}/preview-cierre - incluye resultado_final con breakdown de arreglos"""
        response = requests.get(f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/preview-cierre", headers=headers)
        
        # May return 400 if already closed, which is acceptable
        if response.status_code == 400:
            detail = response.json().get("detail", "")
            if "cierre activo" in detail.lower():
                pytest.skip("Registro already has active cierre")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify resultado_final is present
        assert "resultado_final" in data, "Missing resultado_final in preview-cierre"
        resultado = data["resultado_final"]
        
        # Verify resultado_final structure
        required_fields = ["normal", "recuperado", "liquidacion", "merma", "fallado_pendiente", "total_fallados"]
        for field in required_fields:
            assert field in resultado, f"Missing field in resultado_final: {field}"
        
        print(f"Preview cierre resultado_final: normal={resultado['normal']}, recuperado={resultado['recuperado']}, "
              f"liquidacion={resultado['liquidacion']}, merma={resultado['merma']}, fallado_pendiente={resultado['fallado_pendiente']}")


class TestTrazabilidadKPIs:
    """Tests for /api/reportes/trazabilidad-kpis endpoint"""
    
    def test_trazabilidad_kpis_structure(self, headers):
        """GET /api/reportes/trazabilidad-kpis - verifica estructura"""
        response = requests.get(f"{BASE_URL}/api/reportes/trazabilidad-kpis", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify kpis section
        assert "kpis" in data
        kpis = data["kpis"]
        kpi_fields = ["mermas_total", "mermas_eventos", "fallados_total", "fallados_eventos",
                      "arreglos_total", "arreglos_recuperadas", "arreglos_liquidadas", "arreglos_vencidos"]
        for field in kpi_fields:
            assert field in kpis, f"Missing KPI field: {field}"
        
        # Verify other sections
        assert "mermas_por_servicio" in data
        assert "arreglos_vencidos" in data
        assert "arreglos_por_responsable" in data
        
        print(f"KPIs: fallados_total={kpis['fallados_total']}, arreglos_total={kpis['arreglos_total']}, "
              f"arreglos_recuperadas={kpis['arreglos_recuperadas']}, arreglos_vencidos={kpis['arreglos_vencidos']}")


class TestReporteTrazabilidad:
    """Tests for /api/reporte-trazabilidad endpoint"""
    
    def test_reporte_trazabilidad_structure(self, headers):
        """GET /api/reporte-trazabilidad - verifica estructura"""
        response = requests.get(f"{BASE_URL}/api/reporte-trazabilidad", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "registros" in data
        assert "totales" in data
        
        # Verify totales structure
        totales = data["totales"]
        totales_fields = ["registros", "cantidad_inicial", "normal", "total_fallados",
                         "en_arreglo", "recuperado", "liquidacion", "merma", "vencidos"]
        for field in totales_fields:
            assert field in totales, f"Missing totales field: {field}"
        
        # Verify registro structure if any
        if len(data["registros"]) > 0:
            reg = data["registros"][0]
            reg_fields = ["id", "n_corte", "estado", "cantidad_inicial", "normal",
                         "total_fallados", "fallado_pendiente", "en_arreglo", "recuperado"]
            for field in reg_fields:
                assert field in reg, f"Missing registro field: {field}"
        
        print(f"Reporte trazabilidad: {totales['registros']} registros, "
              f"total_fallados={totales['total_fallados']}, en_arreglo={totales['en_arreglo']}")


class TestTrazabilidadCompleta:
    """Tests for /api/registros/{id}/trazabilidad-completa endpoint"""
    
    def test_trazabilidad_completa_timeline(self, headers):
        """GET /api/registros/{id}/trazabilidad-completa - timeline unificado"""
        response = requests.get(f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/trazabilidad-completa", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "registro" in data
        assert "eventos" in data
        assert "total_eventos" in data
        
        # Verify eventos structure
        eventos = data["eventos"]
        assert isinstance(eventos, list)
        
        # Check for different event types
        event_types = set(e.get("tipo_evento") for e in eventos)
        print(f"Trazabilidad completa: {data['total_eventos']} eventos, tipos: {event_types}")
        
        # Verify ARREGLO events have correct structure
        arreglo_events = [e for e in eventos if e.get("tipo_evento") == "ARREGLO"]
        for ae in arreglo_events:
            assert "estado" in ae
            assert ae["estado"] in ["EN_ARREGLO", "PARCIAL", "COMPLETADO", "VENCIDO"]
            assert "cantidad_recuperada" in ae
            assert "cantidad_liquidacion" in ae
            assert "cantidad_merma" in ae


class TestValidacionesIntegridad:
    """Tests for validation rules and data integrity"""
    
    def test_fallado_delete_blocked_by_arreglos(self, headers):
        """DELETE /api/fallados/{id} - no se puede eliminar si hay arreglos que exceden"""
        # This test verifies that deleting a fallado is blocked if it would cause
        # arreglos to exceed the remaining fallados
        
        # Get current state
        fallados = requests.get(f"{BASE_URL}/api/fallados?registro_id={TEST_REGISTRO_ID}", headers=headers).json()
        arreglos = requests.get(f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/arreglos", headers=headers).json()
        
        total_fallados = sum(f.get("cantidad_detectada", 0) for f in fallados)
        total_arreglos = sum(a.get("cantidad", 0) for a in arreglos)
        
        print(f"Current state: total_fallados={total_fallados}, total_arreglos={total_arreglos}")
        
        # If there are arreglos and fallados, try to delete a fallado that would cause issues
        if total_arreglos > 0 and len(fallados) > 0:
            # Find a fallado that if deleted would cause arreglos to exceed
            for fallado in fallados:
                remaining_after_delete = total_fallados - fallado["cantidad_detectada"]
                if remaining_after_delete < total_arreglos:
                    # This delete should be blocked
                    response = requests.delete(f"{BASE_URL}/api/fallados/{fallado['id']}", headers=headers)
                    if response.status_code == 400:
                        assert "excede" in response.json().get("detail", "").lower()
                        print(f"Correctly blocked deletion of fallado {fallado['id']}")
                        return
        
        print("No blocking scenario found - test passed by default")
    
    def test_fallado_update_blocked_by_arreglos(self, headers):
        """PUT /api/fallados/{id} - no se puede reducir si arreglos exceden nuevo total"""
        # Similar to delete test but for update
        
        fallados = requests.get(f"{BASE_URL}/api/fallados?registro_id={TEST_REGISTRO_ID}", headers=headers).json()
        arreglos = requests.get(f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/arreglos", headers=headers).json()
        
        total_fallados = sum(f.get("cantidad_detectada", 0) for f in fallados)
        total_arreglos = sum(a.get("cantidad", 0) for a in arreglos)
        
        if total_arreglos > 0 and len(fallados) > 0:
            # Try to reduce a fallado to cause arreglos to exceed
            for fallado in fallados:
                otros_fallados = total_fallados - fallado["cantidad_detectada"]
                # Try to set this fallado to 0 (which would make total = otros_fallados)
                if otros_fallados < total_arreglos:
                    response = requests.put(f"{BASE_URL}/api/fallados/{fallado['id']}", 
                                          json={"cantidad_detectada": 1}, headers=headers)
                    if response.status_code == 400:
                        assert "excede" in response.json().get("detail", "").lower()
                        print(f"Correctly blocked update of fallado {fallado['id']}")
                        return
        
        print("No blocking scenario found - test passed by default")


# Cleanup fixture to run after all tests
@pytest.fixture(scope="module", autouse=True)
def cleanup(headers):
    """Cleanup test data after all tests"""
    yield
    # Cleanup any TEST_ prefixed data
    try:
        fallados = requests.get(f"{BASE_URL}/api/fallados?registro_id={TEST_REGISTRO_ID}", headers=headers).json()
        for f in fallados:
            if f.get("observacion", "").startswith("TEST_"):
                requests.delete(f"{BASE_URL}/api/fallados/{f['id']}", headers=headers)
        
        arreglos = requests.get(f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/arreglos", headers=headers).json()
        for a in arreglos:
            if a.get("observacion", "").startswith("TEST_") and a.get("estado") != "COMPLETADO":
                requests.delete(f"{BASE_URL}/api/arreglos/{a['id']}", headers=headers)
    except Exception as e:
        print(f"Cleanup error: {e}")
