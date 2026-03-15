"""
Pytest Test Suite for Textile Production Module
Tests: Reports (WIP, MP, PT, Ordenes, Resumen), Rollos, Consumos, Servicios, Cierre
empresa_id=7 for all tests
"""
import pytest
import requests
import os
from datetime import date

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
EMPRESA_ID = 7

# Test credentials
USERNAME = "eduard"
PASSWORD = "eduard123"

# Known test data
ITEM_TELA_MULTI_ID = "6ab918f1-aa7d-43af-8551-3e52c2204b6f"
ORDER_EN_PROCESO_ID = "80a36f47-989f-4e6e-9bd5-66d502fbcafc"
ORDER_EN_PROCESO_ALT = "00ad4198-6f20-4731-a6d7-9ab9873b45f3"
ORDER_EN_PROCESO_WITH_WIP = "b4d2080f-9e01-4380-ba54-809b1da8f2fa"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def auth_token(api_client):
    """Get authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "username": USERNAME,
        "password": PASSWORD
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    token = response.json().get("access_token")
    assert token, "No access token returned"
    return token


@pytest.fixture(scope="module")
def authenticated_client(api_client, auth_token):
    """Session with auth header"""
    api_client.headers.update({"Authorization": f"Bearer {auth_token}"})
    return api_client


# ==================== REPORT ENDPOINTS ====================

class TestReporteWIP:
    """Tests for GET /api/reportes/wip - WIP Report"""
    
    def test_wip_report_returns_ordenes(self, authenticated_client):
        """WIP report must return ordenes array with correct fields"""
        response = authenticated_client.get(f"{BASE_URL}/api/reportes/wip?empresa_id={EMPRESA_ID}")
        assert response.status_code == 200, f"WIP report failed: {response.text}"
        
        data = response.json()
        
        # Check structure
        assert "ordenes" in data, "Response must have 'ordenes' field"
        assert "resumen" in data, "Response must have 'resumen' field"
        assert "empresa_id" in data, "Response must have 'empresa_id'"
        assert data["empresa_id"] == EMPRESA_ID
        
        # Check resumen fields
        resumen = data["resumen"]
        assert "total_ordenes_en_proceso" in resumen
        assert "total_costo_mp" in resumen
        assert "total_costo_servicio" in resumen
        assert "total_wip" in resumen
        
        # Check ordenes have required fields
        if data["ordenes"]:
            orden = data["ordenes"][0]
            required_fields = ["id", "n_corte", "estado_op", "costo_mp", "costo_servicio", "costo_wip"]
            for field in required_fields:
                assert field in orden, f"Orden missing field: {field}"
    
    def test_wip_report_only_shows_active_orders(self, authenticated_client):
        """WIP should only include ABIERTA and EN_PROCESO orders"""
        response = authenticated_client.get(f"{BASE_URL}/api/reportes/wip?empresa_id={EMPRESA_ID}")
        assert response.status_code == 200
        
        data = response.json()
        for orden in data["ordenes"]:
            assert orden["estado_op"] in ("ABIERTA", "EN_PROCESO"), \
                f"WIP should not include order with estado_op={orden['estado_op']}"


class TestReporteMPValorizado:
    """Tests for GET /api/reportes/mp-valorizado"""
    
    def test_mp_valorizado_returns_items(self, authenticated_client):
        """MP report must return items with valorization fields"""
        response = authenticated_client.get(f"{BASE_URL}/api/reportes/mp-valorizado?empresa_id={EMPRESA_ID}")
        assert response.status_code == 200, f"MP report failed: {response.text}"
        
        data = response.json()
        
        # Check structure
        assert "items" in data, "Response must have 'items' field"
        assert "resumen" in data, "Response must have 'resumen' field"
        
        # Check resumen fields
        resumen = data["resumen"]
        assert "valor_total_inventario" in resumen, "Resumen must have 'valor_total_inventario'"
        assert "total_items" in resumen
    
    def test_mp_valorizado_item_fields(self, authenticated_client):
        """Each MP item must have valor_total, total_reservado, costo_promedio"""
        response = authenticated_client.get(f"{BASE_URL}/api/reportes/mp-valorizado?empresa_id={EMPRESA_ID}")
        assert response.status_code == 200
        
        data = response.json()
        if data["items"]:
            item = data["items"][0]
            required_fields = ["valor_total", "total_reservado", "costo_promedio", "stock_actual", "disponible"]
            for field in required_fields:
                assert field in item, f"Item missing field: {field}"
                # Value should be numeric
                assert isinstance(item[field], (int, float)), f"Field {field} should be numeric"


class TestReportePTValorizado:
    """Tests for GET /api/reportes/pt-valorizado"""
    
    def test_pt_valorizado_returns_items(self, authenticated_client):
        """PT report must return items with valorization fields"""
        response = authenticated_client.get(f"{BASE_URL}/api/reportes/pt-valorizado?empresa_id={EMPRESA_ID}")
        assert response.status_code == 200, f"PT report failed: {response.text}"
        
        data = response.json()
        
        # Check structure
        assert "items" in data, "Response must have 'items' field"
        assert "resumen" in data, "Response must have 'resumen' field"
        
        # Check resumen fields
        resumen = data["resumen"]
        assert "valor_total_pt" in resumen, "Resumen must have 'valor_total_pt'"
        assert "total_skus" in resumen
        assert "total_unidades" in resumen
    
    def test_pt_valorizado_item_fields(self, authenticated_client):
        """Each PT item must have valor_total, total_cierres, costo_promedio"""
        response = authenticated_client.get(f"{BASE_URL}/api/reportes/pt-valorizado?empresa_id={EMPRESA_ID}")
        assert response.status_code == 200
        
        data = response.json()
        if data["items"]:
            item = data["items"][0]
            required_fields = ["valor_total", "total_cierres", "costo_promedio", "stock_actual"]
            for field in required_fields:
                assert field in item, f"PT item missing field: {field}"


class TestReporteResumenGeneral:
    """Tests for GET /api/reportes/resumen-general"""
    
    def test_resumen_general_structure(self, authenticated_client):
        """Resumen general must return inventory totals and order counts"""
        response = authenticated_client.get(f"{BASE_URL}/api/reportes/resumen-general?empresa_id={EMPRESA_ID}")
        assert response.status_code == 200, f"Resumen general failed: {response.text}"
        
        data = response.json()
        
        # Check structure
        assert "inventario" in data
        assert "ordenes" in data
        
        # Check inventario fields
        inv = data["inventario"]
        assert "mp_valor" in inv
        assert "wip_valor" in inv
        assert "pt_valor" in inv
        assert "total" in inv


class TestReporteOrdenes:
    """Tests for GET /api/reportes/ordenes"""
    
    def test_reporte_ordenes_returns_ordenes(self, authenticated_client):
        """Ordenes report must return orders with cost data"""
        response = authenticated_client.get(f"{BASE_URL}/api/reportes/ordenes?empresa_id={EMPRESA_ID}")
        assert response.status_code == 200, f"Ordenes report failed: {response.text}"
        
        data = response.json()
        
        assert "ordenes" in data
        assert "resumen_por_estado" in data
        assert "total_ordenes" in data
        
        if data["ordenes"]:
            orden = data["ordenes"][0]
            cost_fields = ["costo_mp", "costo_servicio", "costo_total"]
            for field in cost_fields:
                assert field in orden, f"Orden missing cost field: {field}"


class TestLegacyEndpointRemoved:
    """Test that legacy endpoint returns 404"""
    
    def test_wip_legacy_returns_404(self, authenticated_client):
        """The legacy /api/reportes/wip-legacy must return 404"""
        response = authenticated_client.get(f"{BASE_URL}/api/reportes/wip-legacy?empresa_id={EMPRESA_ID}")
        assert response.status_code == 404, f"Expected 404 for legacy endpoint, got {response.status_code}"


# ==================== ROLLOS ENDPOINTS ====================

class TestRollosDisponibles:
    """Tests for GET /api/rollos/disponibles/{item_id}"""
    
    def test_rollos_disponibles_returns_rollos(self, authenticated_client):
        """Get available rollos for an item with rollos control"""
        response = authenticated_client.get(f"{BASE_URL}/api/rollos/disponibles/{ITEM_TELA_MULTI_ID}")
        assert response.status_code == 200, f"Rollos disponibles failed: {response.text}"
        
        data = response.json()
        
        assert "item_id" in data
        assert "rollos" in data
        assert "total_disponible" in data
        
        # Check rollos have required fields
        if data["rollos"]:
            rollo = data["rollos"][0]
            required_fields = ["id", "metros_saldo", "costo_unitario_metro", "estado"]
            for field in required_fields:
                assert field in rollo, f"Rollo missing field: {field}"
    
    def test_rollos_disponibles_only_active_with_saldo(self, authenticated_client):
        """Only return rollos with estado=ACTIVO and metros_saldo > 0"""
        response = authenticated_client.get(f"{BASE_URL}/api/rollos/disponibles/{ITEM_TELA_MULTI_ID}")
        assert response.status_code == 200
        
        data = response.json()
        for rollo in data["rollos"]:
            assert rollo["estado"] == "ACTIVO", f"Rollo {rollo['id']} should be ACTIVO"
            assert rollo["metros_saldo"] > 0, f"Rollo {rollo['id']} should have saldo > 0"


# ==================== CONSUMO ENDPOINTS ====================

class TestConsumoSimple:
    """Tests for POST /api/consumos"""
    
    def test_consumo_requires_orden_activa(self, authenticated_client):
        """Cannot consume on closed order"""
        # Try to consume on order that might be closed
        response = authenticated_client.get(f"{BASE_URL}/api/reportes/ordenes?empresa_id={EMPRESA_ID}&estado_op=CERRADA")
        if response.status_code == 200:
            data = response.json()
            if data["ordenes"]:
                closed_orden = data["ordenes"][0]["id"]
                # Try to consume
                consumo_response = authenticated_client.post(f"{BASE_URL}/api/consumos", json={
                    "empresa_id": EMPRESA_ID,
                    "orden_id": closed_orden,
                    "item_id": ITEM_TELA_MULTI_ID,
                    "cantidad": 1
                })
                assert consumo_response.status_code in (400, 422), \
                    f"Should reject consumption on closed order"


class TestConsumoMultiRollo:
    """Tests for POST /api/consumos/multi-rollo"""
    
    def test_multi_rollo_endpoint_exists(self, authenticated_client):
        """Multi-rollo endpoint should exist"""
        # Just test that the endpoint exists and validates input
        response = authenticated_client.post(f"{BASE_URL}/api/consumos/multi-rollo", json={
            "empresa_id": EMPRESA_ID,
            "orden_id": ORDER_EN_PROCESO_ID,
            "item_id": ITEM_TELA_MULTI_ID,
            "rollos": []  # Empty, just testing endpoint exists
        })
        # Should return 200 with empty consumos (no rollos) or 422 validation error
        assert response.status_code in (200, 422), \
            f"Multi-rollo endpoint error: {response.status_code} - {response.text}"


# ==================== SERVICIOS ENDPOINTS ====================

class TestServiciosOrden:
    """Tests for /api/servicios-orden"""
    
    def test_get_servicios_orden(self, authenticated_client):
        """Can list servicios for empresa"""
        response = authenticated_client.get(f"{BASE_URL}/api/servicios-orden?empresa_id={EMPRESA_ID}")
        assert response.status_code == 200, f"Get servicios failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        if data:
            servicio = data[0]
            required_fields = ["id", "orden_id", "costo_total", "estado"]
            for field in required_fields:
                assert field in servicio, f"Servicio missing field: {field}"
    
    def test_create_servicio_orden(self, authenticated_client):
        """Can create a service for an active order"""
        servicio_data = {
            "empresa_id": EMPRESA_ID,
            "orden_id": ORDER_EN_PROCESO_ID,
            "descripcion": "TEST - Servicio pytest",
            "proveedor_texto": "Taller Test",
            "cantidad_enviada": 10,
            "cantidad_recibida": 10,
            "tarifa_unitaria": 5.0,
            "observaciones": "Test service from pytest"
        }
        
        response = authenticated_client.post(f"{BASE_URL}/api/servicios-orden", json=servicio_data)
        assert response.status_code in (200, 201), f"Create servicio failed: {response.text}"
        
        data = response.json()
        assert "id" in data
        assert data["costo_total"] == 50.0  # 10 * 5.0


# ==================== CIERRE ENDPOINTS ====================

class TestCierrePreview:
    """Tests for GET /api/ordenes/{orden_id}/cierre/preview"""
    
    def test_cierre_preview_active_order(self, authenticated_client):
        """Can preview cierre for active order"""
        response = authenticated_client.get(f"{BASE_URL}/api/ordenes/{ORDER_EN_PROCESO_ID}/cierre/preview")
        assert response.status_code == 200, f"Cierre preview failed: {response.text}"
        
        data = response.json()
        
        # Check structure
        assert "ya_cerrada" in data
        assert data["ya_cerrada"] == False
        assert "costos" in data
        
        # Check cost fields
        costos = data["costos"]
        required = ["costo_mp", "costo_servicios", "costo_total", "costo_unitario"]
        for field in required:
            assert field in costos, f"Costos missing field: {field}"
    
    def test_cierre_preview_closed_order_shows_existing(self, authenticated_client):
        """Preview for closed order returns existing cierre"""
        # Find a closed order
        response = authenticated_client.get(f"{BASE_URL}/api/reportes/ordenes?empresa_id={EMPRESA_ID}")
        if response.status_code == 200:
            data = response.json()
            closed_orders = [o for o in data["ordenes"] if o["estado_op"] == "CERRADA"]
            if closed_orders:
                closed_id = closed_orders[0]["id"]
                preview = authenticated_client.get(f"{BASE_URL}/api/ordenes/{closed_id}/cierre/preview")
                assert preview.status_code == 200
                
                preview_data = preview.json()
                assert preview_data["ya_cerrada"] == True


class TestCierreExecution:
    """Tests for POST /api/ordenes/{orden_id}/cierre"""
    
    def test_cierre_validates_pt_required(self, authenticated_client):
        """Cierre should fail if order has no PT assigned"""
        # Order ORDER_EN_PROCESO_ID has no PT
        response = authenticated_client.post(
            f"{BASE_URL}/api/ordenes/{ORDER_EN_PROCESO_ID}/cierre",
            json={
                "cantidad_terminada": 100,
                "otros_costos": 0,
                "observaciones": "Test cierre"
            }
        )
        # Should fail because order has no PT
        assert response.status_code == 400, \
            f"Expected 400 for order without PT, got {response.status_code}"


# ==================== DATA VALIDATION ====================

class TestDataIntegrity:
    """Tests for data consistency across reports"""
    
    def test_wip_total_matches_resumen(self, authenticated_client):
        """WIP total in ordenes should match resumen"""
        response = authenticated_client.get(f"{BASE_URL}/api/reportes/wip?empresa_id={EMPRESA_ID}")
        assert response.status_code == 200
        
        data = response.json()
        
        # Sum costo_wip from all ordenes
        calculated_total = sum(o.get("costo_wip", 0) for o in data["ordenes"])
        reported_total = data["resumen"]["total_wip"]
        
        # Allow small floating point difference
        assert abs(calculated_total - reported_total) < 0.01, \
            f"WIP total mismatch: calculated={calculated_total}, reported={reported_total}"
    
    def test_mp_valor_total_matches_resumen(self, authenticated_client):
        """MP item values should sum to resumen total"""
        response = authenticated_client.get(f"{BASE_URL}/api/reportes/mp-valorizado?empresa_id={EMPRESA_ID}")
        assert response.status_code == 200
        
        data = response.json()
        
        calculated_total = sum(i.get("valor_total", 0) for i in data["items"])
        reported_total = data["resumen"]["valor_total_inventario"]
        
        assert abs(calculated_total - reported_total) < 0.01, \
            f"MP valor total mismatch: calculated={calculated_total}, reported={reported_total}"


# ==================== CLEANUP ====================

@pytest.fixture(scope="module", autouse=True)
def cleanup_test_data(authenticated_client):
    """Cleanup test-created data after all tests"""
    yield
    # Delete test services (those with TEST prefix in description)
    try:
        response = authenticated_client.get(f"{BASE_URL}/api/servicios-orden?empresa_id={EMPRESA_ID}")
        if response.status_code == 200:
            for servicio in response.json():
                if servicio.get("descripcion", "").startswith("TEST"):
                    authenticated_client.delete(f"{BASE_URL}/api/servicios-orden/{servicio['id']}")
    except:
        pass  # Best effort cleanup
