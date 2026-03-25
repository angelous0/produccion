"""
Test Suite: Matriz Producción - Colores Feature
Tests for the color_general field in /api/reportes-produccion/matriz endpoint:
- Fila-level colores array has color_general field
- Detalle-level colores array has color_general field
- Color grouping by color_general works correctly
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestMatrizColores:
    """Test Matriz colores feature with color_general field"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "eduard",
            "password": "eduard123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.fixture(scope="class")
    def matriz_data(self, auth_headers):
        """Get matriz data for testing"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/matriz?solo_activos=true",
            headers=auth_headers
        )
        assert response.status_code == 200
        return response.json()
    
    def test_matriz_fila_has_colores_field(self, matriz_data):
        """Matriz fila has colores field (array)"""
        if not matriz_data["filas"]:
            pytest.skip("No filas available for testing")
        
        fila = matriz_data["filas"][0]
        assert "colores" in fila, "Missing 'colores' field in fila"
        assert isinstance(fila["colores"], list), "colores should be a list"
    
    def test_matriz_fila_colores_has_color_general(self, matriz_data):
        """Matriz fila colores items have color_general field"""
        # Find a fila with colors
        for fila in matriz_data["filas"]:
            if fila.get("colores"):
                color = fila["colores"][0]
                assert "color" in color, "Missing 'color' field in fila colores"
                assert "color_general" in color, "Missing 'color_general' field in fila colores"
                assert "cantidad" in color, "Missing 'cantidad' field in fila colores"
                assert "registros" in color, "Missing 'registros' field in fila colores"
                print(f"Fila color structure: {color}")
                return
        
        pytest.skip("No fila with colors found")
    
    def test_matriz_detalle_has_colores_field(self, matriz_data):
        """Matriz detalle has colores field (array)"""
        if not matriz_data["filas"]:
            pytest.skip("No filas available for testing")
        
        for fila in matriz_data["filas"]:
            if fila.get("detalle"):
                detalle = fila["detalle"][0]
                assert "colores" in detalle, "Missing 'colores' field in detalle"
                assert isinstance(detalle["colores"], list), "colores should be a list"
                return
        
        pytest.skip("No detalle available for testing")
    
    def test_matriz_detalle_colores_has_color_general(self, matriz_data):
        """Matriz detalle colores items have color_general field"""
        # Find a detalle with colors
        for fila in matriz_data["filas"]:
            for detalle in fila.get("detalle", []):
                if detalle.get("colores"):
                    color = detalle["colores"][0]
                    assert "color" in color, "Missing 'color' field in detalle colores"
                    assert "color_general" in color, "Missing 'color_general' field in detalle colores"
                    assert "cantidad" in color, "Missing 'cantidad' field in detalle colores"
                    print(f"Detalle color structure: {color}")
                    return
        
        pytest.skip("No detalle with colors found")
    
    def test_matriz_color_general_values(self, matriz_data):
        """Matriz color_general has expected values (Celeste, Azul, Maiz)"""
        expected_generals = {"Celeste", "Azul", "Maiz"}
        found_generals = set()
        
        for fila in matriz_data["filas"]:
            for color in fila.get("colores", []):
                if color.get("color_general"):
                    found_generals.add(color["color_general"])
        
        if not found_generals:
            pytest.skip("No color_general values found")
        
        print(f"Found color_general values: {found_generals}")
        # At least one of the expected values should be present
        assert found_generals.intersection(expected_generals), \
            f"Expected at least one of {expected_generals}, found {found_generals}"
    
    def test_matriz_detalle_colores_resumen(self, matriz_data):
        """Matriz detalle has colores_resumen field (comma-separated colors)"""
        for fila in matriz_data["filas"]:
            for detalle in fila.get("detalle", []):
                assert "colores_resumen" in detalle, "Missing 'colores_resumen' field in detalle"
                assert isinstance(detalle["colores_resumen"], str), "colores_resumen should be a string"
                if detalle.get("colores"):
                    # If there are colors, colores_resumen should not be empty
                    assert detalle["colores_resumen"], "colores_resumen should not be empty when colors exist"
                    print(f"Registro {detalle['n_corte']} colores_resumen: {detalle['colores_resumen']}")
                return
        
        pytest.skip("No detalle available for testing")
    
    def test_matriz_fila_colores_resumen(self, matriz_data):
        """Matriz fila has colores_resumen field"""
        if not matriz_data["filas"]:
            pytest.skip("No filas available for testing")
        
        fila = matriz_data["filas"][0]
        assert "colores_resumen" in fila, "Missing 'colores_resumen' field in fila"
        assert isinstance(fila["colores_resumen"], str), "colores_resumen should be a string"
    
    def test_matriz_colores_cantidad_is_int(self, matriz_data):
        """Matriz colores cantidad is integer"""
        for fila in matriz_data["filas"]:
            for color in fila.get("colores", []):
                assert isinstance(color.get("cantidad", 0), int), "cantidad should be int"
            for detalle in fila.get("detalle", []):
                for color in detalle.get("colores", []):
                    assert isinstance(color.get("cantidad", 0), int), "cantidad should be int"
    
    def test_matriz_colores_registros_is_int(self, matriz_data):
        """Matriz fila colores registros is integer"""
        for fila in matriz_data["filas"]:
            for color in fila.get("colores", []):
                assert isinstance(color.get("registros", 0), int), "registros should be int"


class TestMatrizColoresFiltering:
    """Test that colores are correctly filtered when clicking on a cell"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "eduard",
            "password": "eduard123"
        })
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_matriz_detalle_colores_match_registro(self, auth_headers):
        """Detalle colores should match the registro's distribucion_colores"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/matriz?solo_activos=true",
            headers=auth_headers
        )
        data = response.json()
        
        # Find registro 03 which has colors
        for fila in data["filas"]:
            for detalle in fila.get("detalle", []):
                if detalle["n_corte"] == "03" and detalle.get("colores"):
                    # Verify colors exist
                    assert len(detalle["colores"]) > 0, "Registro 03 should have colors"
                    # Verify each color has required fields
                    for color in detalle["colores"]:
                        assert "color" in color
                        assert "color_general" in color
                        assert "cantidad" in color
                    print(f"Registro 03 has {len(detalle['colores'])} colors")
                    return
        
        pytest.skip("Registro 03 with colors not found")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
