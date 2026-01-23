"""
Tests for Drag & Drop Reorder functionality and Hilos Específicos CRUD
Tests the new features:
1. Reorder endpoint for all catalog tables
2. Hilos Específicos CRUD operations
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestReorderEndpoint:
    """Tests for PUT /api/reorder/{tabla} endpoint"""
    
    def test_reorder_marcas(self):
        """Test reordering marcas table"""
        # First get existing marcas
        response = requests.get(f"{BASE_URL}/api/marcas")
        assert response.status_code == 200
        marcas = response.json()
        
        if len(marcas) >= 2:
            # Swap order of first two items
            items = [
                {"id": marcas[0]["id"], "orden": 2},
                {"id": marcas[1]["id"], "orden": 1}
            ]
            reorder_response = requests.put(
                f"{BASE_URL}/api/reorder/marcas",
                json={"items": items}
            )
            assert reorder_response.status_code == 200
            data = reorder_response.json()
            assert "message" in data
            assert data["items_updated"] == 2
            print("✓ Reorder marcas works correctly")
    
    def test_reorder_tipos(self):
        """Test reordering tipos table"""
        response = requests.get(f"{BASE_URL}/api/tipos")
        assert response.status_code == 200
        tipos = response.json()
        
        if len(tipos) >= 1:
            items = [{"id": tipos[0]["id"], "orden": 1}]
            reorder_response = requests.put(
                f"{BASE_URL}/api/reorder/tipos",
                json={"items": items}
            )
            assert reorder_response.status_code == 200
            print("✓ Reorder tipos works correctly")
    
    def test_reorder_entalles(self):
        """Test reordering entalles table"""
        response = requests.get(f"{BASE_URL}/api/entalles")
        assert response.status_code == 200
        
        reorder_response = requests.put(
            f"{BASE_URL}/api/reorder/entalles",
            json={"items": []}
        )
        assert reorder_response.status_code == 200
        print("✓ Reorder entalles endpoint accessible")
    
    def test_reorder_telas(self):
        """Test reordering telas table"""
        response = requests.get(f"{BASE_URL}/api/telas")
        assert response.status_code == 200
        
        reorder_response = requests.put(
            f"{BASE_URL}/api/reorder/telas",
            json={"items": []}
        )
        assert reorder_response.status_code == 200
        print("✓ Reorder telas endpoint accessible")
    
    def test_reorder_hilos(self):
        """Test reordering hilos table"""
        response = requests.get(f"{BASE_URL}/api/hilos")
        assert response.status_code == 200
        
        reorder_response = requests.put(
            f"{BASE_URL}/api/reorder/hilos",
            json={"items": []}
        )
        assert reorder_response.status_code == 200
        print("✓ Reorder hilos endpoint accessible")
    
    def test_reorder_tallas_catalogo(self):
        """Test reordering tallas-catalogo table"""
        response = requests.get(f"{BASE_URL}/api/tallas-catalogo")
        assert response.status_code == 200
        
        reorder_response = requests.put(
            f"{BASE_URL}/api/reorder/tallas-catalogo",
            json={"items": []}
        )
        assert reorder_response.status_code == 200
        print("✓ Reorder tallas-catalogo endpoint accessible")
    
    def test_reorder_colores_generales(self):
        """Test reordering colores-generales table"""
        response = requests.get(f"{BASE_URL}/api/colores-generales")
        assert response.status_code == 200
        
        reorder_response = requests.put(
            f"{BASE_URL}/api/reorder/colores-generales",
            json={"items": []}
        )
        assert reorder_response.status_code == 200
        print("✓ Reorder colores-generales endpoint accessible")
    
    def test_reorder_colores_catalogo(self):
        """Test reordering colores-catalogo table"""
        response = requests.get(f"{BASE_URL}/api/colores-catalogo")
        assert response.status_code == 200
        
        reorder_response = requests.put(
            f"{BASE_URL}/api/reorder/colores-catalogo",
            json={"items": []}
        )
        assert reorder_response.status_code == 200
        print("✓ Reorder colores-catalogo endpoint accessible")
    
    def test_reorder_hilos_especificos(self):
        """Test reordering hilos-especificos table"""
        response = requests.get(f"{BASE_URL}/api/hilos-especificos")
        assert response.status_code == 200
        
        reorder_response = requests.put(
            f"{BASE_URL}/api/reorder/hilos-especificos",
            json={"items": []}
        )
        assert reorder_response.status_code == 200
        print("✓ Reorder hilos-especificos endpoint accessible")
    
    def test_reorder_invalid_table_returns_400(self):
        """Test that invalid table name returns 400 error"""
        response = requests.put(
            f"{BASE_URL}/api/reorder/invalid-table",
            json={"items": []}
        )
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "no permitida" in data["detail"]
        print("✓ Invalid table returns 400 error correctly")


class TestHilosEspecificosCRUD:
    """Tests for Hilos Específicos CRUD operations"""
    
    @pytest.fixture
    def test_hilo_id(self):
        """Create a test hilo específico and return its ID"""
        response = requests.post(
            f"{BASE_URL}/api/hilos-especificos",
            json={
                "nombre": f"TEST_Hilo_{uuid.uuid4().hex[:8]}",
                "codigo": f"HE-{uuid.uuid4().hex[:4]}",
                "color": "Rojo Test",
                "descripcion": "Test description"
            }
        )
        assert response.status_code == 200
        data = response.json()
        yield data["id"]
        # Cleanup
        requests.delete(f"{BASE_URL}/api/hilos-especificos/{data['id']}")
    
    def test_list_hilos_especificos(self):
        """Test GET /api/hilos-especificos"""
        response = requests.get(f"{BASE_URL}/api/hilos-especificos")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ List hilos específicos: {len(data)} items")
    
    def test_create_hilo_especifico(self):
        """Test POST /api/hilos-especificos"""
        test_name = f"TEST_Hilo_Create_{uuid.uuid4().hex[:8]}"
        response = requests.post(
            f"{BASE_URL}/api/hilos-especificos",
            json={
                "nombre": test_name,
                "codigo": "HE-CREATE",
                "color": "Azul",
                "descripcion": "Created for testing"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["nombre"] == test_name
        assert data["codigo"] == "HE-CREATE"
        assert data["color"] == "Azul"
        assert "id" in data
        assert "orden" in data
        print(f"✓ Create hilo específico: {data['id']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/hilos-especificos/{data['id']}")
    
    def test_create_hilo_especifico_auto_orden(self):
        """Test that orden is auto-assigned when 0"""
        response = requests.post(
            f"{BASE_URL}/api/hilos-especificos",
            json={
                "nombre": f"TEST_Hilo_AutoOrden_{uuid.uuid4().hex[:8]}",
                "codigo": "HE-AUTO",
                "color": "Verde",
                "descripcion": "",
                "orden": 0
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["orden"] > 0  # Should be auto-assigned
        print(f"✓ Auto-orden assigned: {data['orden']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/hilos-especificos/{data['id']}")
    
    def test_update_hilo_especifico(self, test_hilo_id):
        """Test PUT /api/hilos-especificos/{id}"""
        response = requests.put(
            f"{BASE_URL}/api/hilos-especificos/{test_hilo_id}",
            json={
                "nombre": "TEST_Updated_Name",
                "codigo": "HE-UPD",
                "color": "Amarillo",
                "descripcion": "Updated description",
                "orden": 99
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["nombre"] == "TEST_Updated_Name"
        assert data["codigo"] == "HE-UPD"
        assert data["color"] == "Amarillo"
        print(f"✓ Update hilo específico: {test_hilo_id}")
    
    def test_update_nonexistent_hilo_returns_404(self):
        """Test that updating non-existent hilo returns 404"""
        fake_id = str(uuid.uuid4())
        response = requests.put(
            f"{BASE_URL}/api/hilos-especificos/{fake_id}",
            json={
                "nombre": "Test",
                "codigo": "TEST",
                "color": "Test",
                "descripcion": "",
                "orden": 1
            }
        )
        assert response.status_code == 404
        print("✓ Update non-existent returns 404")
    
    def test_delete_hilo_especifico(self):
        """Test DELETE /api/hilos-especificos/{id}"""
        # Create one to delete
        create_response = requests.post(
            f"{BASE_URL}/api/hilos-especificos",
            json={
                "nombre": f"TEST_ToDelete_{uuid.uuid4().hex[:8]}",
                "codigo": "HE-DEL",
                "color": "Negro",
                "descripcion": ""
            }
        )
        assert create_response.status_code == 200
        hilo_id = create_response.json()["id"]
        
        # Delete it
        delete_response = requests.delete(f"{BASE_URL}/api/hilos-especificos/{hilo_id}")
        assert delete_response.status_code == 200
        data = delete_response.json()
        assert "message" in data
        print(f"✓ Delete hilo específico: {hilo_id}")
        
        # Verify it's gone
        list_response = requests.get(f"{BASE_URL}/api/hilos-especificos")
        hilos = list_response.json()
        assert not any(h["id"] == hilo_id for h in hilos)
        print("✓ Verified deletion")


class TestMarcasCRUDWithOrden:
    """Test that Marcas CRUD includes orden field"""
    
    def test_marcas_have_orden_field(self):
        """Test that marcas list includes orden field"""
        response = requests.get(f"{BASE_URL}/api/marcas")
        assert response.status_code == 200
        marcas = response.json()
        if len(marcas) > 0:
            assert "orden" in marcas[0]
            print(f"✓ Marcas have orden field: {marcas[0].get('orden')}")
    
    def test_create_marca_with_orden(self):
        """Test creating marca with orden"""
        test_name = f"TEST_Marca_{uuid.uuid4().hex[:8]}"
        response = requests.post(
            f"{BASE_URL}/api/marcas",
            json={"nombre": test_name, "orden": 0}
        )
        assert response.status_code == 200
        data = response.json()
        assert "orden" in data
        assert data["orden"] > 0  # Auto-assigned
        print(f"✓ Create marca with auto-orden: {data['orden']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/marcas/{data['id']}")


class TestTiposCRUDWithOrden:
    """Test that Tipos CRUD includes orden field"""
    
    def test_tipos_have_orden_field(self):
        """Test that tipos list includes orden field"""
        response = requests.get(f"{BASE_URL}/api/tipos")
        assert response.status_code == 200
        tipos = response.json()
        if len(tipos) > 0:
            assert "orden" in tipos[0]
            print(f"✓ Tipos have orden field: {tipos[0].get('orden')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
