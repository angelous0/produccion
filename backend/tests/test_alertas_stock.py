"""
Test suite for Stock Alerts (Alertas de Stock Bajo) feature
Tests the new endpoints for low stock alerts and ignore functionality
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username": "eduard",
        "password": "eduard123"
    }, timeout=120)
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Authentication failed - skipping tests")

@pytest.fixture
def api_client(auth_token):
    """Shared requests session with auth"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session


class TestAlertasStockEndpoint:
    """Tests for GET /api/inventario/alertas-stock endpoint"""
    
    def test_alertas_stock_basic(self, api_client):
        """Test basic alertas-stock endpoint returns expected structure"""
        response = api_client.get(f"{BASE_URL}/api/inventario/alertas-stock", timeout=30)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify response structure
        assert "items" in data, "Response should have 'items' field"
        assert "total" in data, "Response should have 'total' field"
        assert "sin_stock" in data, "Response should have 'sin_stock' field"
        assert "stock_bajo" in data, "Response should have 'stock_bajo' field"
        assert "modo" in data, "Response should have 'modo' field"
        
        # Default mode should be 'fisico'
        assert data["modo"] == "fisico", f"Default mode should be 'fisico', got {data['modo']}"
        
        # Total should match sin_stock + stock_bajo
        assert data["total"] == data["sin_stock"] + data["stock_bajo"], \
            f"Total ({data['total']}) should equal sin_stock ({data['sin_stock']}) + stock_bajo ({data['stock_bajo']})"
        
        print(f"✓ Alertas stock basic: {data['total']} items ({data['sin_stock']} sin stock, {data['stock_bajo']} stock bajo)")
    
    def test_alertas_stock_modo_fisico(self, api_client):
        """Test alertas-stock with modo=fisico"""
        response = api_client.get(f"{BASE_URL}/api/inventario/alertas-stock?modo=fisico", timeout=30)
        assert response.status_code == 200
        
        data = response.json()
        assert data["modo"] == "fisico"
        
        # Verify items have expected fields
        if data["items"]:
            item = data["items"][0]
            assert "id" in item
            assert "codigo" in item
            assert "nombre" in item
            assert "stock_actual" in item
            assert "stock_minimo" in item
            assert "stock_disponible" in item
            assert "total_reservado" in item
            assert "faltante" in item
            assert "estado_stock" in item
            assert item["estado_stock"] in ["SIN_STOCK", "STOCK_BAJO"]
            print(f"✓ Modo fisico: Item '{item['nombre']}' - stock_actual={item['stock_actual']}, stock_minimo={item['stock_minimo']}")
    
    def test_alertas_stock_modo_disponible(self, api_client):
        """Test alertas-stock with modo=disponible (considers reservations)"""
        response = api_client.get(f"{BASE_URL}/api/inventario/alertas-stock?modo=disponible", timeout=30)
        assert response.status_code == 200
        
        data = response.json()
        assert data["modo"] == "disponible"
        
        # Verify items have stock_disponible calculated
        if data["items"]:
            item = data["items"][0]
            # stock_disponible should be stock_actual - total_reservado
            expected_disponible = max(0, item["stock_actual"] - item["total_reservado"])
            assert item["stock_disponible"] == expected_disponible, \
                f"stock_disponible should be {expected_disponible}, got {item['stock_disponible']}"
            print(f"✓ Modo disponible: Item '{item['nombre']}' - disponible={item['stock_disponible']}")
    
    def test_alertas_stock_incluir_ignorados(self, api_client):
        """Test alertas-stock with incluir_ignorados=true"""
        # First get without ignored
        response_without = api_client.get(f"{BASE_URL}/api/inventario/alertas-stock", timeout=30)
        assert response_without.status_code == 200
        count_without = response_without.json()["total"]
        
        # Then get with ignored
        response_with = api_client.get(f"{BASE_URL}/api/inventario/alertas-stock?incluir_ignorados=true", timeout=30)
        assert response_with.status_code == 200
        count_with = response_with.json()["total"]
        
        # Count with ignored should be >= count without
        assert count_with >= count_without, \
            f"Count with ignored ({count_with}) should be >= count without ({count_without})"
        print(f"✓ Incluir ignorados: {count_without} active, {count_with} total (including ignored)")


class TestIgnorarAlertaEndpoint:
    """Tests for PUT /api/inventario/{item_id}/ignorar-alerta endpoint"""
    
    def test_toggle_ignorar_alerta(self, api_client):
        """Test toggling ignore flag on an item"""
        # First get an item with stock alert
        alertas_response = api_client.get(f"{BASE_URL}/api/inventario/alertas-stock?incluir_ignorados=true", timeout=30)
        assert alertas_response.status_code == 200
        
        items = alertas_response.json()["items"]
        if not items:
            pytest.skip("No items with stock alerts to test")
        
        item = items[0]
        item_id = item["id"]
        original_ignorar = item.get("ignorar_alerta_stock", False)
        
        # Toggle the ignore flag
        toggle_response = api_client.put(f"{BASE_URL}/api/inventario/{item_id}/ignorar-alerta", timeout=30)
        assert toggle_response.status_code == 200, f"Expected 200, got {toggle_response.status_code}: {toggle_response.text}"
        
        toggle_data = toggle_response.json()
        assert "id" in toggle_data
        assert "ignorar_alerta_stock" in toggle_data
        assert toggle_data["ignorar_alerta_stock"] == (not original_ignorar), \
            f"Expected ignorar_alerta_stock to be {not original_ignorar}, got {toggle_data['ignorar_alerta_stock']}"
        
        print(f"✓ Toggle ignorar: Item {item_id} changed from {original_ignorar} to {toggle_data['ignorar_alerta_stock']}")
        
        # Toggle back to original state
        toggle_back = api_client.put(f"{BASE_URL}/api/inventario/{item_id}/ignorar-alerta", timeout=30)
        assert toggle_back.status_code == 200
        assert toggle_back.json()["ignorar_alerta_stock"] == original_ignorar
        print(f"✓ Toggle back: Item {item_id} restored to {original_ignorar}")
    
    def test_toggle_ignorar_nonexistent_item(self, api_client):
        """Test toggling ignore flag on non-existent item returns 404"""
        response = api_client.put(f"{BASE_URL}/api/inventario/nonexistent-id-12345/ignorar-alerta", timeout=30)
        assert response.status_code == 404, f"Expected 404 for non-existent item, got {response.status_code}"
        print("✓ Non-existent item returns 404")


class TestStatsAlertasStock:
    """Tests for alertas_stock fields in GET /api/stats endpoint"""
    
    def test_stats_includes_alertas_stock(self, api_client):
        """Test that /api/stats includes stock alert counts"""
        response = api_client.get(f"{BASE_URL}/api/stats", timeout=30)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify alertas_stock fields exist
        assert "alertas_stock_total" in data, "Stats should include 'alertas_stock_total'"
        assert "stock_bajo" in data, "Stats should include 'stock_bajo'"
        assert "sin_stock" in data, "Stats should include 'sin_stock'"
        
        # Verify consistency
        assert data["alertas_stock_total"] == data["stock_bajo"] + data["sin_stock"], \
            f"alertas_stock_total ({data['alertas_stock_total']}) should equal stock_bajo ({data['stock_bajo']}) + sin_stock ({data['sin_stock']})"
        
        print(f"✓ Stats alertas: total={data['alertas_stock_total']}, stock_bajo={data['stock_bajo']}, sin_stock={data['sin_stock']}")
    
    def test_stats_alertas_match_endpoint(self, api_client):
        """Test that stats alertas counts match alertas-stock endpoint"""
        # Get stats
        stats_response = api_client.get(f"{BASE_URL}/api/stats", timeout=30)
        assert stats_response.status_code == 200
        stats = stats_response.json()
        
        # Get alertas-stock
        alertas_response = api_client.get(f"{BASE_URL}/api/inventario/alertas-stock", timeout=30)
        assert alertas_response.status_code == 200
        alertas = alertas_response.json()
        
        # Compare counts (should match since both exclude ignored items by default)
        assert stats["alertas_stock_total"] == alertas["total"], \
            f"Stats total ({stats['alertas_stock_total']}) should match alertas total ({alertas['total']})"
        assert stats["stock_bajo"] == alertas["stock_bajo"], \
            f"Stats stock_bajo ({stats['stock_bajo']}) should match alertas stock_bajo ({alertas['stock_bajo']})"
        assert stats["sin_stock"] == alertas["sin_stock"], \
            f"Stats sin_stock ({stats['sin_stock']}) should match alertas sin_stock ({alertas['sin_stock']})"
        
        print(f"✓ Stats and alertas-stock endpoint counts match")


class TestAlertasStockDataIntegrity:
    """Tests for data integrity in stock alerts"""
    
    def test_only_items_with_stock_minimo_configured(self, api_client):
        """Test that only items with stock_minimo > 0 appear in alerts"""
        response = api_client.get(f"{BASE_URL}/api/inventario/alertas-stock?incluir_ignorados=true", timeout=30)
        assert response.status_code == 200
        
        items = response.json()["items"]
        for item in items:
            assert item["stock_minimo"] > 0, \
                f"Item '{item['nombre']}' has stock_minimo={item['stock_minimo']}, should be > 0"
        
        print(f"✓ All {len(items)} items have stock_minimo > 0")
    
    def test_items_actually_have_low_stock(self, api_client):
        """Test that items in alerts actually have stock below minimum"""
        response = api_client.get(f"{BASE_URL}/api/inventario/alertas-stock", timeout=30)
        assert response.status_code == 200
        
        items = response.json()["items"]
        for item in items:
            # In fisico mode, stock_actual should be <= stock_minimo
            assert item["stock_actual"] <= item["stock_minimo"], \
                f"Item '{item['nombre']}' has stock_actual={item['stock_actual']} > stock_minimo={item['stock_minimo']}"
        
        print(f"✓ All {len(items)} items have stock_actual <= stock_minimo")
    
    def test_estado_stock_classification(self, api_client):
        """Test that estado_stock is correctly classified"""
        response = api_client.get(f"{BASE_URL}/api/inventario/alertas-stock", timeout=30)
        assert response.status_code == 200
        
        items = response.json()["items"]
        for item in items:
            if item["stock_actual"] <= 0:
                assert item["estado_stock"] == "SIN_STOCK", \
                    f"Item '{item['nombre']}' with stock_actual={item['stock_actual']} should be SIN_STOCK"
            else:
                assert item["estado_stock"] == "STOCK_BAJO", \
                    f"Item '{item['nombre']}' with stock_actual={item['stock_actual']} should be STOCK_BAJO"
        
        print(f"✓ All items have correct estado_stock classification")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
