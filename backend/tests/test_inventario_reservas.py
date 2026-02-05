"""
Test suite for Inventario Reservas feature
Tests the new functionality for showing available stock (stock_disponible) 
and reservation details in the inventory page.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://production-hub-67.preview.emergentagent.com')

class TestInventarioReservas:
    """Tests for inventory reservations feature"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Login and get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "eduard",
            "password": "eduard123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_inventario_returns_total_reservado(self):
        """GET /api/inventario should return total_reservado field for each item"""
        response = requests.get(f"{BASE_URL}/api/inventario", headers=self.headers)
        assert response.status_code == 200
        
        items = response.json()
        assert len(items) > 0, "No inventory items found"
        
        # Check that all items have total_reservado field
        for item in items:
            assert "total_reservado" in item, f"Item {item.get('codigo')} missing total_reservado"
            assert isinstance(item["total_reservado"], (int, float)), "total_reservado should be numeric"
    
    def test_get_inventario_returns_stock_disponible(self):
        """GET /api/inventario should return stock_disponible field for each item"""
        response = requests.get(f"{BASE_URL}/api/inventario", headers=self.headers)
        assert response.status_code == 200
        
        items = response.json()
        assert len(items) > 0, "No inventory items found"
        
        # Check that all items have stock_disponible field
        for item in items:
            assert "stock_disponible" in item, f"Item {item.get('codigo')} missing stock_disponible"
            assert isinstance(item["stock_disponible"], (int, float)), "stock_disponible should be numeric"
    
    def test_stock_disponible_calculation(self):
        """stock_disponible should equal stock_actual - total_reservado"""
        response = requests.get(f"{BASE_URL}/api/inventario", headers=self.headers)
        assert response.status_code == 200
        
        items = response.json()
        for item in items:
            expected_disponible = max(0, item["stock_actual"] - item["total_reservado"])
            assert item["stock_disponible"] == expected_disponible, \
                f"Item {item.get('codigo')}: stock_disponible ({item['stock_disponible']}) != " \
                f"stock_actual ({item['stock_actual']}) - total_reservado ({item['total_reservado']})"
    
    def test_items_with_reservations_exist(self):
        """Verify there are items with active reservations for testing"""
        response = requests.get(f"{BASE_URL}/api/inventario", headers=self.headers)
        assert response.status_code == 200
        
        items = response.json()
        items_with_reservations = [i for i in items if i["total_reservado"] > 0]
        
        assert len(items_with_reservations) > 0, "No items with active reservations found"
        print(f"Found {len(items_with_reservations)} items with active reservations:")
        for item in items_with_reservations:
            print(f"  - {item['codigo']}: {item['nombre']} (reservado: {item['total_reservado']})")
    
    def test_get_reservas_detalle_endpoint_exists(self):
        """GET /api/inventario/{item_id}/reservas-detalle should exist"""
        # First get an item with reservations
        response = requests.get(f"{BASE_URL}/api/inventario", headers=self.headers)
        assert response.status_code == 200
        
        items = response.json()
        items_with_reservations = [i for i in items if i["total_reservado"] > 0]
        
        if len(items_with_reservations) == 0:
            pytest.skip("No items with reservations to test")
        
        item = items_with_reservations[0]
        
        # Test the reservas-detalle endpoint
        response = requests.get(
            f"{BASE_URL}/api/inventario/{item['id']}/reservas-detalle", 
            headers=self.headers
        )
        assert response.status_code == 200, f"reservas-detalle endpoint failed: {response.text}"
    
    def test_reservas_detalle_structure(self):
        """GET /api/inventario/{item_id}/reservas-detalle should return correct structure"""
        # First get an item with reservations
        response = requests.get(f"{BASE_URL}/api/inventario", headers=self.headers)
        items = response.json()
        items_with_reservations = [i for i in items if i["total_reservado"] > 0]
        
        if len(items_with_reservations) == 0:
            pytest.skip("No items with reservations to test")
        
        item = items_with_reservations[0]
        
        # Get reservas-detalle
        response = requests.get(
            f"{BASE_URL}/api/inventario/{item['id']}/reservas-detalle", 
            headers=self.headers
        )
        assert response.status_code == 200
        
        data = response.json()
        
        # Check required fields in response
        required_fields = ['item_id', 'item_codigo', 'item_nombre', 'stock_actual', 
                          'total_reservado', 'stock_disponible', 'registros']
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
        # Check registros structure
        assert isinstance(data['registros'], list), "registros should be a list"
        
        if len(data['registros']) > 0:
            registro = data['registros'][0]
            registro_fields = ['registro_id', 'n_corte', 'registro_estado', 
                              'modelo_nombre', 'total_reservado', 'lineas']
            for field in registro_fields:
                assert field in registro, f"Missing field in registro: {field}"
    
    def test_reservas_detalle_data_consistency(self):
        """Verify data consistency between inventario and reservas-detalle endpoints"""
        # Get inventory
        response = requests.get(f"{BASE_URL}/api/inventario", headers=self.headers)
        items = response.json()
        items_with_reservations = [i for i in items if i["total_reservado"] > 0]
        
        if len(items_with_reservations) == 0:
            pytest.skip("No items with reservations to test")
        
        for item in items_with_reservations:
            # Get reservas-detalle for this item
            response = requests.get(
                f"{BASE_URL}/api/inventario/{item['id']}/reservas-detalle", 
                headers=self.headers
            )
            assert response.status_code == 200
            
            detail = response.json()
            
            # Verify consistency
            assert detail['stock_actual'] == item['stock_actual'], \
                f"stock_actual mismatch for {item['codigo']}"
            assert detail['total_reservado'] == item['total_reservado'], \
                f"total_reservado mismatch for {item['codigo']}"
            assert detail['stock_disponible'] == item['stock_disponible'], \
                f"stock_disponible mismatch for {item['codigo']}"
    
    def test_reservas_detalle_for_item_without_reservations(self):
        """GET /api/inventario/{item_id}/reservas-detalle for item without reservations"""
        # Get an item without reservations
        response = requests.get(f"{BASE_URL}/api/inventario", headers=self.headers)
        items = response.json()
        items_without_reservations = [i for i in items if i["total_reservado"] == 0]
        
        if len(items_without_reservations) == 0:
            pytest.skip("No items without reservations to test")
        
        item = items_without_reservations[0]
        
        # Get reservas-detalle
        response = requests.get(
            f"{BASE_URL}/api/inventario/{item['id']}/reservas-detalle", 
            headers=self.headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data['total_reservado'] == 0
        assert data['registros'] == []
    
    def test_reservas_detalle_invalid_item_id(self):
        """GET /api/inventario/{item_id}/reservas-detalle with invalid ID should return 404"""
        response = requests.get(
            f"{BASE_URL}/api/inventario/invalid-item-id-12345/reservas-detalle", 
            headers=self.headers
        )
        assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
