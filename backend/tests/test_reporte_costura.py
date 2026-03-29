"""
Test: Reporte Operativo de Costura
Tests for GET /api/reportes-produccion/costura and PUT /api/reportes-produccion/costura/avance/{movimiento_id}
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_USERNAME = "eduard"
TEST_PASSWORD = "eduard123"

# Known test data from agent context
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


class TestReporteCosturaEndpoint:
    """Tests for GET /api/reportes-produccion/costura"""

    def test_get_costura_report_returns_200(self, auth_headers):
        """Test that costura report endpoint returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/costura",
            headers=auth_headers,
            timeout=60
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ GET /api/reportes-produccion/costura returned 200")

    def test_costura_report_has_kpis(self, auth_headers):
        """Test that response contains kpis object with expected fields"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/costura",
            headers=auth_headers,
            timeout=60
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "kpis" in data, "Response should contain 'kpis'"
        kpis = data["kpis"]
        
        expected_kpi_fields = [
            "costureros_activos",
            "registros_activos",
            "total_prendas",
            "registros_vencidos",
            "registros_criticos",
            "registros_sin_actualizar",
            "incidencias_abiertas"
        ]
        
        for field in expected_kpi_fields:
            assert field in kpis, f"KPIs should contain '{field}'"
            assert isinstance(kpis[field], int), f"KPI '{field}' should be an integer"
        
        print(f"✓ KPIs present: costureros={kpis['costureros_activos']}, registros={kpis['registros_activos']}, prendas={kpis['total_prendas']}")

    def test_costura_report_has_items(self, auth_headers):
        """Test that response contains items array"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/costura",
            headers=auth_headers,
            timeout=60
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "items" in data, "Response should contain 'items'"
        assert isinstance(data["items"], list), "'items' should be a list"
        print(f"✓ Items array present with {len(data['items'])} items")

    def test_costura_report_has_filtros(self, auth_headers):
        """Test that response contains filtros object"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/costura",
            headers=auth_headers,
            timeout=60
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "filtros" in data, "Response should contain 'filtros'"
        assert "personas" in data["filtros"], "Filtros should contain 'personas'"
        print(f"✓ Filtros present with {len(data['filtros']['personas'])} personas")

    def test_costura_item_structure(self, auth_headers):
        """Test that each item has expected fields"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/costura",
            headers=auth_headers,
            timeout=60
        )
        assert response.status_code == 200
        data = response.json()
        
        if len(data["items"]) == 0:
            pytest.skip("No items in costura report to validate structure")
        
        item = data["items"][0]
        expected_fields = [
            "movimiento_id",
            "registro_id",
            "persona_id",
            "persona_nombre",
            "n_corte",
            "modelo_nombre",
            "tipo_nombre",
            "entalle_nombre",
            "tela_nombre",
            "cantidad_enviada",
            "avance_porcentaje",
            "pendiente_estimado",
            "fecha_inicio",
            "fecha_esperada",
            "dias_transcurridos",
            "dias_sin_actualizar",
            "incidencias_abiertas",
            "nivel_riesgo"
        ]
        
        for field in expected_fields:
            assert field in item, f"Item should contain '{field}'"
        
        print(f"✓ Item structure valid: {item['n_corte']} - {item['persona_nombre']} - riesgo={item['nivel_riesgo']}")

    def test_costura_filter_by_riesgo(self, auth_headers):
        """Test filtering by riesgo parameter"""
        # First get all items
        response_all = requests.get(
            f"{BASE_URL}/api/reportes-produccion/costura",
            headers=auth_headers,
            timeout=60
        )
        assert response_all.status_code == 200
        all_items = response_all.json()["items"]
        
        # Filter by atencion
        response_atencion = requests.get(
            f"{BASE_URL}/api/reportes-produccion/costura?riesgo=atencion",
            headers=auth_headers,
            timeout=60
        )
        assert response_atencion.status_code == 200
        atencion_items = response_atencion.json()["items"]
        
        # All filtered items should have nivel_riesgo = atencion
        for item in atencion_items:
            assert item["nivel_riesgo"] == "atencion", f"Expected riesgo=atencion, got {item['nivel_riesgo']}"
        
        print(f"✓ Filter by riesgo works: {len(atencion_items)} items with riesgo=atencion out of {len(all_items)} total")

    def test_costura_filter_by_con_incidencias(self, auth_headers):
        """Test filtering by con_incidencias parameter"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/costura?con_incidencias=true",
            headers=auth_headers,
            timeout=60
        )
        assert response.status_code == 200
        items = response.json()["items"]
        
        # All filtered items should have incidencias_abiertas > 0
        for item in items:
            assert item["incidencias_abiertas"] > 0, f"Expected incidencias > 0, got {item['incidencias_abiertas']}"
        
        print(f"✓ Filter by con_incidencias=true works: {len(items)} items with incidencias")

    def test_pendiente_estimado_calculation(self, auth_headers):
        """Test that pendiente_estimado = cantidad * (1 - avance/100)"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/costura",
            headers=auth_headers,
            timeout=60
        )
        assert response.status_code == 200
        items = response.json()["items"]
        
        for item in items:
            if item["cantidad_enviada"] and item["avance_porcentaje"] is not None:
                expected = round(item["cantidad_enviada"] * (1 - item["avance_porcentaje"] / 100))
                assert item["pendiente_estimado"] == expected, \
                    f"Pendiente mismatch: expected {expected}, got {item['pendiente_estimado']}"
        
        print(f"✓ Pendiente estimado calculation verified for {len(items)} items")

    def test_risk_calculation_atencion_with_incidencias(self, auth_headers):
        """Test that items with incidencias_abiertas >= 1 have riesgo >= atencion"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/costura",
            headers=auth_headers,
            timeout=60
        )
        assert response.status_code == 200
        items = response.json()["items"]
        
        items_with_incidencias = [i for i in items if i["incidencias_abiertas"] >= 1]
        
        for item in items_with_incidencias:
            # Items with incidencias should have at least atencion risk (score >= 1)
            assert item["nivel_riesgo"] in ["atencion", "critico", "vencido"], \
                f"Item with {item['incidencias_abiertas']} incidencias should have riesgo >= atencion, got {item['nivel_riesgo']}"
        
        print(f"✓ Risk calculation verified: {len(items_with_incidencias)} items with incidencias have appropriate risk level")


class TestAvanceRapidoEndpoint:
    """Tests for PUT /api/reportes-produccion/costura/avance/{movimiento_id}"""

    def test_update_avance_returns_200(self, auth_headers):
        """Test that updating avance returns 200"""
        response = requests.put(
            f"{BASE_URL}/api/reportes-produccion/costura/avance/{TEST_MOVIMIENTO_ID}",
            json={"avance_porcentaje": 40},
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["ok"] == True
        assert data["avance_porcentaje"] == 40
        print(f"✓ PUT avance returned 200 with ok=True")

    def test_update_avance_persists(self, auth_headers):
        """Test that avance update persists in database"""
        # Update to 45%
        update_response = requests.put(
            f"{BASE_URL}/api/reportes-produccion/costura/avance/{TEST_MOVIMIENTO_ID}",
            json={"avance_porcentaje": 45},
            headers=auth_headers,
            timeout=30
        )
        assert update_response.status_code == 200
        
        # Verify by fetching the report
        get_response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/costura",
            headers=auth_headers,
            timeout=60
        )
        assert get_response.status_code == 200
        
        items = get_response.json()["items"]
        item = next((i for i in items if i["movimiento_id"] == TEST_MOVIMIENTO_ID), None)
        
        if item:
            assert item["avance_porcentaje"] == 45, f"Expected avance=45, got {item['avance_porcentaje']}"
            assert item["avance_updated_at"] is not None, "avance_updated_at should be set"
            print(f"✓ Avance persisted: {item['avance_porcentaje']}%, updated_at={item['avance_updated_at']}")
        else:
            pytest.skip(f"Movimiento {TEST_MOVIMIENTO_ID} not found in costura report")

    def test_update_avance_invalid_movimiento(self, auth_headers):
        """Test that updating non-existent movimiento returns 404"""
        response = requests.put(
            f"{BASE_URL}/api/reportes-produccion/costura/avance/invalid-uuid-12345",
            json={"avance_porcentaje": 50},
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ Invalid movimiento returns 404")

    def test_update_avance_restores_original(self, auth_headers):
        """Restore original avance value (35%) after tests"""
        response = requests.put(
            f"{BASE_URL}/api/reportes-produccion/costura/avance/{TEST_MOVIMIENTO_ID}",
            json={"avance_porcentaje": 35},
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200
        print(f"✓ Restored avance to 35%")


class TestCosturaReportDataValidation:
    """Validate specific test data mentioned in agent context"""

    def test_pepe_perez_movimiento_exists(self, auth_headers):
        """Verify the test movimiento for Pepe Perez exists with expected data"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/costura",
            headers=auth_headers,
            timeout=60
        )
        assert response.status_code == 200
        
        items = response.json()["items"]
        item = next((i for i in items if i["movimiento_id"] == TEST_MOVIMIENTO_ID), None)
        
        if item is None:
            pytest.skip(f"Test movimiento {TEST_MOVIMIENTO_ID} not found")
        
        # Validate expected data from agent context
        assert item["persona_nombre"] == "Pepe Perez", f"Expected persona=Pepe Perez, got {item['persona_nombre']}"
        assert item["servicio_nombre"].lower() == "costura", f"Expected servicio=Costura, got {item['servicio_nombre']}"
        assert item["n_corte"] == "01", f"Expected n_corte=01, got {item['n_corte']}"
        assert item["cantidad_enviada"] == 500, f"Expected cantidad=500, got {item['cantidad_enviada']}"
        
        print(f"✓ Test data validated: {item['persona_nombre']} - {item['n_corte']} - {item['cantidad_enviada']} prendas")

    def test_incidencia_abierta_affects_risk(self, auth_headers):
        """Verify that the 1 open incidencia affects risk level"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/costura",
            headers=auth_headers,
            timeout=60
        )
        assert response.status_code == 200
        
        items = response.json()["items"]
        item = next((i for i in items if i["movimiento_id"] == TEST_MOVIMIENTO_ID), None)
        
        if item is None:
            pytest.skip(f"Test movimiento {TEST_MOVIMIENTO_ID} not found")
        
        # According to agent context: 1 incidencia abierta, riesgo=atencion
        assert item["incidencias_abiertas"] >= 1, f"Expected incidencias >= 1, got {item['incidencias_abiertas']}"
        # With 1 incidencia, risk should be at least atencion
        assert item["nivel_riesgo"] in ["atencion", "critico", "vencido"], \
            f"Expected riesgo >= atencion with incidencias, got {item['nivel_riesgo']}"
        
        print(f"✓ Risk calculation correct: {item['incidencias_abiertas']} incidencias -> riesgo={item['nivel_riesgo']}")
