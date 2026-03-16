"""
BOM Explosion → Requerimiento MP Tests
Tests for:
- POST /api/bom/explosion/{orden_id} - Generate MP requirement from BOM
- POST /api/bom/explosion/{orden_id} with regenerar=true - Replace existing requirement
- POST /api/bom/explosion/{orden_id} without BOM - 404 error
- POST /api/bom/explosion/{orden_id} for closed order - 400 error
- GET /api/bom/requerimiento/{orden_id} - Get requirement with stock, deficit, cost
- Calculation validation: cantidad_requerida = cantidad_total_bom * total_prendas_orden
- SERVICIO lines excluded from requirement
- Non-regression: GET /api/reportes/wip, mp-valorizado, pt-valorizado
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://bom-pricing-update.preview.emergentagent.com').rstrip('/')

# Test data from problem statement
ORDER_WITH_BOM_ID = "b4d2080f-9e01-4380-ba54-809b1da8f2fa"  # n_corte=10, 500 prendas, has 3 requerimiento lines
ORDER_NO_TALLAS_ID = "80a36f47-989f-4e6e-9bd5-66d502fbcafc"  # n_corte=11, EN_PROCESO, no tallas
CLOSED_ORDER_ID = "7647ad65-188f-47d2-890e-bb7802ea0f65"  # estado_op=CERRADA
BOM_JEAN_CLASSIC_ID = "94f2e969-459b-4f65-83b9-add8a5838e1f"  # BOM-JEAN-CLASS-V2, APROBADO
MODELO_JEAN_CLASSIC_ID = "29510110-c662-4b4b-9243-cbea55f015ff"

# Inventario IDs
INV_TELA_ALGODON_ID = "91135a62-b4d5-4df9-8516-c64709f77b91"  # costo=5.5
INV_DENIM_ID = "7711bfd5-178d-4287-a2d8-9fb75ff1bb74"  # costo=12.5  
INV_BOTON_ID = "cabbd10c-84c9-49b4-9610-deef3a573fa6"  # costo=1.0


@pytest.fixture
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


class TestBomExplosionEndpoint:
    """Tests for POST /api/bom/explosion/{orden_id}"""
    
    def test_explosion_order_not_found(self, api_client):
        """POST /api/bom/explosion/{orden_id} - Order not found returns 404"""
        response = api_client.post(f"{BASE_URL}/api/bom/explosion/non-existent-order-id", json={
            "empresa_id": 7
        })
        assert response.status_code == 404
        assert "no encontrada" in response.json().get("detail", "").lower()
    
    def test_explosion_closed_order_returns_400(self, api_client):
        """POST /api/bom/explosion/{orden_id} for closed order returns 400"""
        response = api_client.post(f"{BASE_URL}/api/bom/explosion/{CLOSED_ORDER_ID}", json={
            "empresa_id": 7
        })
        assert response.status_code == 400
        detail = response.json().get("detail", "").lower()
        assert "cerrada" in detail or "closed" in detail
    
    def test_explosion_no_tallas_returns_400(self, api_client):
        """POST /api/bom/explosion/{orden_id} for order without tallas returns 400"""
        response = api_client.post(f"{BASE_URL}/api/bom/explosion/{ORDER_NO_TALLAS_ID}", json={
            "empresa_id": 7
        })
        assert response.status_code == 400
        detail = response.json().get("detail", "").lower()
        assert "tallas" in detail or "cantidades" in detail
    
    def test_explosion_existing_requerimiento_without_regenerar_returns_409(self, api_client):
        """POST /api/bom/explosion/{orden_id} when requerimiento exists without regenerar=true returns 409"""
        # Order b4d2080f already has 3 requerimiento lines
        response = api_client.post(f"{BASE_URL}/api/bom/explosion/{ORDER_WITH_BOM_ID}", json={
            "empresa_id": 7,
            "regenerar": False
        })
        assert response.status_code == 409
        detail = response.json().get("detail", "")
        assert "Ya existe" in detail or "regenerar" in detail
    
    def test_explosion_with_regenerar_replaces_requerimiento(self, api_client):
        """POST /api/bom/explosion/{orden_id} with regenerar=true replaces existing requirement"""
        response = api_client.post(f"{BASE_URL}/api/bom/explosion/{ORDER_WITH_BOM_ID}", json={
            "empresa_id": 7,
            "regenerar": True
        })
        assert response.status_code == 200
        data = response.json()
        
        # Validate response structure
        assert data["orden_id"] == ORDER_WITH_BOM_ID
        assert data["n_corte"] == "10"
        assert "bom_id" in data
        assert "bom_codigo" in data
        assert "total_prendas" in data
        assert data["total_prendas"] == 500  # 100+150+150+100 from tallas
        assert "requerimiento_mp" in data
        assert "servicios_estandar" in data
        assert "resumen" in data
        
        # Validate resumen
        resumen = data["resumen"]
        assert "total_lineas_mp" in resumen
        assert "total_costo_mp_estimado" in resumen
        assert "items_con_deficit" in resumen
        assert resumen["total_lineas_mp"] > 0
    
    def test_explosion_calculates_cantidad_requerida_correctly(self, api_client):
        """Validate calculation: cantidad_requerida = cantidad_total_bom * total_prendas"""
        response = api_client.post(f"{BASE_URL}/api/bom/explosion/{ORDER_WITH_BOM_ID}", json={
            "empresa_id": 7,
            "regenerar": True
        })
        assert response.status_code == 200
        data = response.json()
        
        total_prendas = data["total_prendas"]
        assert total_prendas == 500
        
        # BOM-JEAN-CLASS-V2 has 3 lines:
        # - Tela Algodón: base=1.5, merma=3%, total=1.545 → req = 1.545 * 500 = 772.5
        # - Denim: base=0.8, merma=5%, total=0.84 → req = 0.84 * 500 = 420
        # - Boton: base=4.0, merma=2%, total=4.08 → req = 4.08 * 500 = 2040
        
        req_mp = data["requerimiento_mp"]
        
        # Find each item and validate calculation
        tela_algodon = next((r for r in req_mp if r["item_id"] == INV_TELA_ALGODON_ID), None)
        if tela_algodon:
            # cantidad_total_bom = 1.545, total_prendas = 500
            expected = 1.545 * 500  # = 772.5
            assert abs(tela_algodon["cantidad_requerida"] - expected) < 0.1, \
                f"Tela Algodón expected {expected}, got {tela_algodon['cantidad_requerida']}"
        
        denim = next((r for r in req_mp if r["item_id"] == INV_DENIM_ID), None)
        if denim:
            expected = 0.84 * 500  # = 420
            assert abs(denim["cantidad_requerida"] - expected) < 0.1, \
                f"Denim expected {expected}, got {denim['cantidad_requerida']}"
        
        boton = next((r for r in req_mp if r["item_id"] == INV_BOTON_ID), None)
        if boton:
            expected = 4.08 * 500  # = 2040
            assert abs(boton["cantidad_requerida"] - expected) < 0.1, \
                f"Boton expected {expected}, got {boton['cantidad_requerida']}"
    
    def test_explosion_calculates_deficit_correctly(self, api_client):
        """Validate deficit = max(0, requerido - stock)"""
        response = api_client.post(f"{BASE_URL}/api/bom/explosion/{ORDER_WITH_BOM_ID}", json={
            "empresa_id": 7,
            "regenerar": True
        })
        assert response.status_code == 200
        data = response.json()
        
        for item in data["requerimiento_mp"]:
            requerido = item["cantidad_requerida"]
            stock = item["stock_actual"]
            deficit = item["deficit"]
            
            expected_deficit = max(0, requerido - stock)
            assert abs(deficit - expected_deficit) < 0.01, \
                f"Item {item['inventario_nombre']}: deficit expected {expected_deficit}, got {deficit}"
    
    def test_explosion_servicio_not_in_requerimiento(self, api_client):
        """Validate that SERVICIO type lines are NOT in requerimiento_mp"""
        response = api_client.post(f"{BASE_URL}/api/bom/explosion/{ORDER_WITH_BOM_ID}", json={
            "empresa_id": 7,
            "regenerar": True
        })
        assert response.status_code == 200
        data = response.json()
        
        req_mp = data["requerimiento_mp"]
        for item in req_mp:
            tipo = item.get("tipo_componente", "")
            assert tipo != "SERVICIO", f"SERVICIO found in requerimiento_mp: {item['inventario_nombre']}"
        
        # Servicios should be in servicios_estandar (referential only)
        # Check that all MP types are allowed
        allowed_types = ["TELA", "AVIO", "EMPAQUE", "OTRO"]
        for item in req_mp:
            tipo = item.get("tipo_componente", "TELA")
            assert tipo in allowed_types, f"Unexpected tipo_componente: {tipo}"


class TestRequerimientoEndpoint:
    """Tests for GET /api/bom/requerimiento/{orden_id}"""
    
    def test_get_requerimiento_success(self, api_client):
        """GET /api/bom/requerimiento/{orden_id} returns requirement data"""
        response = api_client.get(f"{BASE_URL}/api/bom/requerimiento/{ORDER_WITH_BOM_ID}")
        assert response.status_code == 200
        data = response.json()
        
        # Validate structure
        assert data["orden_id"] == ORDER_WITH_BOM_ID
        assert data["n_corte"] == "10"
        assert "total_lineas" in data
        assert "items" in data
        assert data["total_lineas"] == len(data["items"])
    
    def test_get_requerimiento_items_have_required_fields(self, api_client):
        """Validate each item has stock_actual, deficit, costo_estimado fields"""
        response = api_client.get(f"{BASE_URL}/api/bom/requerimiento/{ORDER_WITH_BOM_ID}")
        assert response.status_code == 200
        data = response.json()
        
        required_fields = [
            "id", "item_id", "cantidad_requerida", "cantidad_reservada", 
            "cantidad_consumida", "estado", "tipo_componente", "inventario_nombre",
            "stock_actual", "deficit", "costo_estimado"
        ]
        
        for item in data["items"]:
            for field in required_fields:
                assert field in item, f"Missing field '{field}' in requerimiento item"
    
    def test_get_requerimiento_deficit_calculation(self, api_client):
        """Validate deficit = max(0, requerido - stock) in GET response"""
        response = api_client.get(f"{BASE_URL}/api/bom/requerimiento/{ORDER_WITH_BOM_ID}")
        assert response.status_code == 200
        data = response.json()
        
        for item in data["items"]:
            requerido = float(item["cantidad_requerida"])
            stock = float(item.get("stock_actual", 0))
            deficit = float(item["deficit"])
            
            expected_deficit = max(0, requerido - stock)
            assert abs(deficit - expected_deficit) < 0.01, \
                f"Item {item['inventario_nombre']}: deficit expected {expected_deficit}, got {deficit}"
    
    def test_get_requerimiento_order_not_found(self, api_client):
        """GET /api/bom/requerimiento/{orden_id} - Order not found returns 404"""
        response = api_client.get(f"{BASE_URL}/api/bom/requerimiento/non-existent-order-id")
        assert response.status_code == 404
    
    def test_get_requerimiento_empty_for_new_order(self, api_client):
        """GET /api/bom/requerimiento/{orden_id} returns empty items for order without requerimiento"""
        # Order 11 has no requerimiento generated (no tallas)
        response = api_client.get(f"{BASE_URL}/api/bom/requerimiento/{ORDER_NO_TALLAS_ID}")
        assert response.status_code == 200
        data = response.json()
        
        # Should have empty items array
        assert data["total_lineas"] == 0
        assert len(data["items"]) == 0


class TestNonRegressionReportes:
    """Non-regression tests for valorizacion reports (require authentication)"""
    
    @pytest.fixture
    def auth_token(self, api_client):
        """Get auth token for protected endpoints"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "username": "eduard",
            "password": "eduard123"
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Authentication failed - skipping protected endpoint tests")
    
    def test_wip_report_still_works(self, api_client, auth_token):
        """GET /api/reportes/wip still returns correct data"""
        api_client.headers.update({"Authorization": f"Bearer {auth_token}"})
        response = api_client.get(f"{BASE_URL}/api/reportes/wip?empresa_id=7")
        assert response.status_code == 200
        data = response.json()
        
        assert "ordenes" in data
        assert isinstance(data["ordenes"], list)
        
        # Validate structure if any orders exist
        if len(data["ordenes"]) > 0:
            orden = data["ordenes"][0]
            assert "estado_op" in orden or "estado" in orden
    
    def test_mp_valorizado_report_still_works(self, api_client, auth_token):
        """GET /api/reportes/mp-valorizado still returns correct data"""
        api_client.headers.update({"Authorization": f"Bearer {auth_token}"})
        response = api_client.get(f"{BASE_URL}/api/reportes/mp-valorizado?empresa_id=7")
        assert response.status_code == 200
        data = response.json()
        
        assert "items" in data
        assert isinstance(data["items"], list)
        
        # Validate structure
        if len(data["items"]) > 0:
            item = data["items"][0]
            assert "valor_total" in item or "costo_promedio" in item
    
    def test_pt_valorizado_report_still_works(self, api_client, auth_token):
        """GET /api/reportes/pt-valorizado still returns correct data"""
        api_client.headers.update({"Authorization": f"Bearer {auth_token}"})
        response = api_client.get(f"{BASE_URL}/api/reportes/pt-valorizado?empresa_id=7")
        assert response.status_code == 200
        data = response.json()
        
        assert "items" in data
        assert isinstance(data["items"], list)


class TestBomLookup:
    """Tests for BOM lookup during explosion"""
    
    def test_explosion_finds_best_bom_aprobado_first(self, api_client):
        """Explosion should find APROBADO BOM before BORRADOR"""
        response = api_client.post(f"{BASE_URL}/api/bom/explosion/{ORDER_WITH_BOM_ID}", json={
            "empresa_id": 7,
            "regenerar": True
        })
        assert response.status_code == 200
        data = response.json()
        
        # Should use BOM-JEAN-CLASS-V2 (APROBADO) not BOM-SINNOMBRE-V1 (BORRADOR)
        assert data["bom_estado"] == "APROBADO"
        assert data["bom_codigo"] == "BOM-JEAN-CLASS-V2"
    
    def test_explosion_with_specific_bom_id(self, api_client):
        """Explosion with specific bom_id uses that BOM"""
        response = api_client.post(f"{BASE_URL}/api/bom/explosion/{ORDER_WITH_BOM_ID}", json={
            "empresa_id": 7,
            "bom_id": BOM_JEAN_CLASSIC_ID,
            "regenerar": True
        })
        assert response.status_code == 200
        data = response.json()
        
        assert data["bom_id"] == BOM_JEAN_CLASSIC_ID


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
