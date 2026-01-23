"""
Test suite for Colores Generales and Colores Catalogo features
Tests:
1. CRUD completo de Colores Generales
2. Crear/Editar color en Colores Catalogo con selector de Color General
3. Verificar que la columna 'Color General' muestra el nombre correctamente
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestColoresGenerales:
    """Test CRUD operations for Colores Generales"""
    
    test_color_general_id = None
    
    def test_01_list_colores_generales(self):
        """GET /api/colores-generales - List all colores generales"""
        response = requests.get(f"{BASE_URL}/api/colores-generales")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Listed {len(data)} colores generales")
        
    def test_02_create_color_general(self):
        """POST /api/colores-generales - Create new color general"""
        payload = {"nombre": f"TEST_ColorGeneral_{uuid.uuid4().hex[:6]}"}
        response = requests.post(f"{BASE_URL}/api/colores-generales", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["nombre"] == payload["nombre"]
        TestColoresGenerales.test_color_general_id = data["id"]
        print(f"✓ Created color general: {data['nombre']} (id: {data['id']})")
        
    def test_03_get_color_general_after_create(self):
        """Verify color general exists after creation"""
        response = requests.get(f"{BASE_URL}/api/colores-generales")
        assert response.status_code == 200
        data = response.json()
        found = any(cg["id"] == TestColoresGenerales.test_color_general_id for cg in data)
        assert found, "Created color general not found in list"
        print(f"✓ Verified color general exists in list")
        
    def test_04_update_color_general(self):
        """PUT /api/colores-generales/{id} - Update color general"""
        new_name = f"TEST_Updated_{uuid.uuid4().hex[:6]}"
        payload = {"nombre": new_name}
        response = requests.put(
            f"{BASE_URL}/api/colores-generales/{TestColoresGenerales.test_color_general_id}",
            json=payload
        )
        assert response.status_code == 200
        data = response.json()
        assert data["nombre"] == new_name
        print(f"✓ Updated color general to: {new_name}")
        
    def test_05_duplicate_name_validation(self):
        """POST /api/colores-generales - Should reject duplicate names"""
        # First get an existing color general
        response = requests.get(f"{BASE_URL}/api/colores-generales")
        data = response.json()
        if len(data) > 0:
            existing_name = data[0]["nombre"]
            payload = {"nombre": existing_name}
            response = requests.post(f"{BASE_URL}/api/colores-generales", json=payload)
            assert response.status_code == 400
            print(f"✓ Duplicate name validation works")
        else:
            pytest.skip("No existing colores generales to test duplicate validation")
            
    def test_06_delete_color_general(self):
        """DELETE /api/colores-generales/{id} - Delete color general"""
        response = requests.delete(
            f"{BASE_URL}/api/colores-generales/{TestColoresGenerales.test_color_general_id}"
        )
        assert response.status_code == 200
        print(f"✓ Deleted color general")
        
    def test_07_verify_deletion(self):
        """Verify color general no longer exists after deletion"""
        response = requests.get(f"{BASE_URL}/api/colores-generales")
        assert response.status_code == 200
        data = response.json()
        found = any(cg["id"] == TestColoresGenerales.test_color_general_id for cg in data)
        assert not found, "Deleted color general still exists"
        print(f"✓ Verified color general was deleted")


class TestColoresCatalogo:
    """Test Colores Catalogo with Color General selector"""
    
    test_color_general_id = None
    test_color_catalogo_id = None
    
    @classmethod
    def setup_class(cls):
        """Create a color general for testing"""
        payload = {"nombre": f"TEST_CG_ForCatalogo_{uuid.uuid4().hex[:6]}"}
        response = requests.post(f"{BASE_URL}/api/colores-generales", json=payload)
        if response.status_code == 200:
            cls.test_color_general_id = response.json()["id"]
            print(f"Setup: Created color general for testing: {cls.test_color_general_id}")
    
    @classmethod
    def teardown_class(cls):
        """Cleanup test data"""
        if cls.test_color_catalogo_id:
            requests.delete(f"{BASE_URL}/api/colores-catalogo/{cls.test_color_catalogo_id}")
        if cls.test_color_general_id:
            requests.delete(f"{BASE_URL}/api/colores-generales/{cls.test_color_general_id}")
        print("Teardown: Cleaned up test data")
    
    def test_01_list_colores_catalogo(self):
        """GET /api/colores-catalogo - List all colors with color_general_nombre"""
        response = requests.get(f"{BASE_URL}/api/colores-catalogo")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Verify response includes color_general_nombre field
        if len(data) > 0:
            assert "color_general_nombre" in data[0], "Response should include color_general_nombre"
        print(f"✓ Listed {len(data)} colores catalogo with color_general_nombre field")
        
    def test_02_create_color_with_color_general(self):
        """POST /api/colores-catalogo - Create color with color_general_id (selector)"""
        payload = {
            "nombre": f"TEST_ColorCatalogo_{uuid.uuid4().hex[:6]}",
            "codigo_hex": "#FF5733",
            "color_general_id": TestColoresCatalogo.test_color_general_id
        }
        response = requests.post(f"{BASE_URL}/api/colores-catalogo", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["nombre"] == payload["nombre"]
        assert data["color_general_id"] == TestColoresCatalogo.test_color_general_id
        TestColoresCatalogo.test_color_catalogo_id = data["id"]
        print(f"✓ Created color catalogo with color_general_id: {data['id']}")
        
    def test_03_verify_color_general_nombre_in_list(self):
        """Verify color_general_nombre is returned correctly in list"""
        response = requests.get(f"{BASE_URL}/api/colores-catalogo")
        assert response.status_code == 200
        data = response.json()
        
        # Find our test color
        test_color = next((c for c in data if c["id"] == TestColoresCatalogo.test_color_catalogo_id), None)
        assert test_color is not None, "Test color not found in list"
        assert test_color.get("color_general_nombre") is not None, "color_general_nombre should not be None"
        print(f"✓ Color general nombre displayed: {test_color['color_general_nombre']}")
        
    def test_04_update_color_change_color_general(self):
        """PUT /api/colores-catalogo/{id} - Update color and change color_general"""
        # Create another color general for testing update
        new_cg_payload = {"nombre": f"TEST_CG_New_{uuid.uuid4().hex[:6]}"}
        new_cg_response = requests.post(f"{BASE_URL}/api/colores-generales", json=new_cg_payload)
        assert new_cg_response.status_code == 200
        new_cg_id = new_cg_response.json()["id"]
        
        try:
            # Update the color to use new color general
            update_payload = {
                "nombre": f"TEST_Updated_{uuid.uuid4().hex[:6]}",
                "codigo_hex": "#00FF00",
                "color_general_id": new_cg_id
            }
            response = requests.put(
                f"{BASE_URL}/api/colores-catalogo/{TestColoresCatalogo.test_color_catalogo_id}",
                json=update_payload
            )
            assert response.status_code == 200
            data = response.json()
            assert data["color_general_id"] == new_cg_id
            print(f"✓ Updated color to use new color_general_id: {new_cg_id}")
        finally:
            # Cleanup the new color general
            requests.delete(f"{BASE_URL}/api/colores-generales/{new_cg_id}")
            
    def test_05_create_color_without_color_general(self):
        """POST /api/colores-catalogo - Create color without color_general_id"""
        payload = {
            "nombre": f"TEST_NoColorGeneral_{uuid.uuid4().hex[:6]}",
            "codigo_hex": "#AABBCC",
            "color_general_id": None
        }
        response = requests.post(f"{BASE_URL}/api/colores-catalogo", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data.get("color_general_id") is None
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/colores-catalogo/{data['id']}")
        print(f"✓ Created color without color_general_id successfully")
        
    def test_06_delete_color_general_with_colors_blocked(self):
        """DELETE /api/colores-generales/{id} - Should be blocked if colors use it"""
        # First create a color general and a color using it
        cg_payload = {"nombre": f"TEST_CG_ToBlock_{uuid.uuid4().hex[:6]}"}
        cg_response = requests.post(f"{BASE_URL}/api/colores-generales", json=cg_payload)
        assert cg_response.status_code == 200
        cg_id = cg_response.json()["id"]
        
        color_payload = {
            "nombre": f"TEST_ColorBlocking_{uuid.uuid4().hex[:6]}",
            "codigo_hex": "#123456",
            "color_general_id": cg_id
        }
        color_response = requests.post(f"{BASE_URL}/api/colores-catalogo", json=color_payload)
        assert color_response.status_code == 200
        color_id = color_response.json()["id"]
        
        try:
            # Try to delete the color general - should be blocked
            delete_response = requests.delete(f"{BASE_URL}/api/colores-generales/{cg_id}")
            assert delete_response.status_code == 400
            assert "No se puede eliminar" in delete_response.json().get("detail", "")
            print(f"✓ Delete blocked correctly when colors use the color general")
        finally:
            # Cleanup
            requests.delete(f"{BASE_URL}/api/colores-catalogo/{color_id}")
            requests.delete(f"{BASE_URL}/api/colores-generales/{cg_id}")


class TestInventarioSalidas:
    """Test Salida de Rollos dialog functionality"""
    
    def test_01_get_inventario_items(self):
        """GET /api/inventario - List items to verify control_por_rollos field"""
        response = requests.get(f"{BASE_URL}/api/inventario")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Check if any items have control_por_rollos
        items_with_rollos = [i for i in data if i.get("control_por_rollos")]
        print(f"✓ Found {len(items_with_rollos)} items with control_por_rollos=true out of {len(data)} total")
        
    def test_02_get_inventario_rollos(self):
        """GET /api/inventario-rollos - List rollos for items"""
        response = requests.get(f"{BASE_URL}/api/inventario-rollos")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Found {len(data)} rollos in inventory")
        
    def test_03_get_inventario_salidas(self):
        """GET /api/inventario-salidas - List salidas"""
        response = requests.get(f"{BASE_URL}/api/inventario-salidas")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Found {len(data)} salidas in inventory")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
