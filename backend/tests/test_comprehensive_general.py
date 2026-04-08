"""
Comprehensive General Test Suite for Textile Management System
Tests all major endpoints: auth, registros, modelos, movimientos, inventario, motivos
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://kardex-pt-sync.preview.emergentagent.com')

# Test credentials
TEST_USERNAME = "eduard"
TEST_PASSWORD = "eduard123"

class TestAuthentication:
    """Authentication endpoint tests"""
    
    def test_login_success(self):
        """Test successful login with valid credentials"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
            timeout=20
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["username"] == TEST_USERNAME
        assert data["user"]["rol"] == "admin"
        print(f"✓ Login successful for user: {data['user']['username']}")
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "invalid_user", "password": "wrong_pass"},
            timeout=20
        )
        assert response.status_code == 401
        print("✓ Invalid credentials correctly rejected")


class TestRegistros:
    """Registros (Production Records) endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token for authenticated requests"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
            timeout=20
        )
        self.token = response.json().get("access_token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_registros_list_paginated(self):
        """Test GET /api/registros with pagination returns correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/registros?limit=50&offset=0",
            timeout=30
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Verify pagination structure
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)
        assert isinstance(data["total"], int)
        
        # Verify required fields in items
        if len(data["items"]) > 0:
            item = data["items"][0]
            required_fields = [
                "id", "n_corte", "modelo_id", "estado", "fecha_creacion",
                "modelo_nombre", "marca_nombre", "tipo_nombre", "entalle_nombre",
                "tela_nombre", "hilo_nombre", "estado_operativo"
            ]
            for field in required_fields:
                assert field in item, f"Missing field: {field}"
        
        print(f"✓ Registros list: {len(data['items'])} of {data['total']} records")
    
    def test_registros_estados(self):
        """Test GET /api/registros-estados returns available states"""
        response = requests.get(f"{BASE_URL}/api/registros-estados", timeout=20)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        print(f"✓ Estados disponibles: {len(data)} estados")
    
    def test_registros_search(self):
        """Test registros search by N Corte"""
        response = requests.get(
            f"{BASE_URL}/api/registros?limit=10&offset=0&search=100",
            timeout=30
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        print(f"✓ Search returned {len(data['items'])} results")
    
    def test_registros_filter_by_estado(self):
        """Test registros filter by estado"""
        response = requests.get(
            f"{BASE_URL}/api/registros?limit=10&offset=0&estados=Para Corte",
            timeout=30
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        # Verify all items have the filtered estado
        for item in data["items"]:
            assert item["estado"] == "Para Corte", f"Wrong estado: {item['estado']}"
        print(f"✓ Estado filter returned {len(data['items'])} results")


class TestModelos:
    """Modelos endpoint tests"""
    
    def test_modelos_list_paginated(self):
        """Test GET /api/modelos with pagination"""
        response = requests.get(
            f"{BASE_URL}/api/modelos?limit=50&offset=0",
            timeout=30
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Verify pagination structure
        assert "items" in data
        assert "total" in data
        
        if len(data["items"]) > 0:
            item = data["items"][0]
            assert "id" in item
            assert "nombre" in item
            assert "marca_id" in item
        
        print(f"✓ Modelos list: {len(data['items'])} of {data['total']} records")
    
    def test_modelos_all_true(self):
        """Test GET /api/modelos?all=true returns array for dropdowns"""
        response = requests.get(
            f"{BASE_URL}/api/modelos?all=true",
            timeout=30
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list), "all=true should return array"
        print(f"✓ Modelos all=true: {len(data)} records")


class TestMovimientosProduccion:
    """Movimientos de Produccion endpoint tests"""
    
    def test_movimientos_list_paginated(self):
        """Test GET /api/movimientos-produccion with pagination and JOINed names"""
        response = requests.get(
            f"{BASE_URL}/api/movimientos-produccion?limit=50&offset=0",
            timeout=30
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "items" in data
        assert "total" in data
        
        if len(data["items"]) > 0:
            item = data["items"][0]
            # Verify JOINed fields are present
            assert "servicio_nombre" in item, "Missing servicio_nombre"
            assert "persona_nombre" in item, "Missing persona_nombre"
            assert "registro_n_corte" in item, "Missing registro_n_corte"
        
        print(f"✓ Movimientos list: {len(data['items'])} of {data['total']} records")
    
    def test_movimientos_search(self):
        """Test movimientos search"""
        response = requests.get(
            f"{BASE_URL}/api/movimientos-produccion?limit=10&offset=0&search=100",
            timeout=30
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        print(f"✓ Movimientos search returned {len(data['items'])} results")


class TestInventario:
    """Inventario endpoint tests"""
    
    def test_inventario_list_paginated(self):
        """Test GET /api/inventario with pagination"""
        response = requests.get(
            f"{BASE_URL}/api/inventario?limit=50&offset=0",
            timeout=30
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "items" in data
        assert "total" in data
        
        if len(data["items"]) > 0:
            item = data["items"][0]
            assert "id" in item
            assert "nombre" in item or "codigo" in item
        
        print(f"✓ Inventario list: {len(data['items'])} of {data['total']} records")
    
    def test_inventario_search(self):
        """Test inventario search by nombre/codigo"""
        response = requests.get(
            f"{BASE_URL}/api/inventario?limit=10&offset=0&search=tela",
            timeout=30
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        print(f"✓ Inventario search returned {len(data['items'])} results")
    
    def test_inventario_filter_categoria(self):
        """Test inventario filter by categoria"""
        response = requests.get(
            f"{BASE_URL}/api/inventario?limit=10&offset=0&categoria=Otros",
            timeout=30
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        print(f"✓ Inventario categoria filter returned {len(data['items'])} results")


class TestMotivosIncidencia:
    """Motivos de Incidencia catalog tests"""
    
    def test_motivos_list(self):
        """Test GET /api/motivos-incidencia returns catalog"""
        response = requests.get(f"{BASE_URL}/api/motivos-incidencia", timeout=20)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) > 0
        
        # Verify structure
        item = data[0]
        assert "id" in item
        assert "nombre" in item
        assert "activo" in item
        
        print(f"✓ Motivos incidencia: {len(data)} motivos")
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
            timeout=20
        )
        self.token = response.json().get("access_token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_motivos_create(self):
        """Test POST /api/motivos-incidencia creates new motivo"""
        test_nombre = f"TEST_Motivo_{int(time.time())}"
        response = requests.post(
            f"{BASE_URL}/api/motivos-incidencia",
            json={"nombre": test_nombre},
            headers=self.headers,
            timeout=20
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data["nombre"] == test_nombre
        print(f"✓ Created motivo: {test_nombre}")
        
        # Cleanup - delete the test motivo
        try:
            requests.delete(
                f"{BASE_URL}/api/motivos-incidencia/{data['id']}",
                headers=self.headers,
                timeout=20
            )
        except:
            pass


class TestMaestros:
    """Maestros (Master data) endpoint tests"""
    
    def test_servicios_produccion(self):
        """Test GET /api/servicios-produccion"""
        response = requests.get(f"{BASE_URL}/api/servicios-produccion", timeout=20)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Servicios produccion: {len(data)} servicios")
    
    def test_personas_produccion(self):
        """Test GET /api/personas-produccion"""
        response = requests.get(f"{BASE_URL}/api/personas-produccion", timeout=20)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Personas produccion: {len(data)} personas")
    
    def test_marcas(self):
        """Test GET /api/marcas"""
        response = requests.get(f"{BASE_URL}/api/marcas", timeout=20)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Marcas: {len(data)} marcas")
    
    def test_tipos(self):
        """Test GET /api/tipos"""
        response = requests.get(f"{BASE_URL}/api/tipos", timeout=20)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Tipos: {len(data)} tipos")
    
    def test_entalles(self):
        """Test GET /api/entalles"""
        response = requests.get(f"{BASE_URL}/api/entalles", timeout=20)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Entalles: {len(data)} entalles")
    
    def test_telas(self):
        """Test GET /api/telas"""
        response = requests.get(f"{BASE_URL}/api/telas", timeout=20)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Telas: {len(data)} telas")
    
    def test_hilos(self):
        """Test GET /api/hilos"""
        response = requests.get(f"{BASE_URL}/api/hilos", timeout=20)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Hilos: {len(data)} hilos")
    
    def test_tallas_catalogo(self):
        """Test GET /api/tallas-catalogo"""
        response = requests.get(f"{BASE_URL}/api/tallas-catalogo", timeout=20)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Tallas catalogo: {len(data)} tallas")
    
    def test_colores_catalogo(self):
        """Test GET /api/colores-catalogo"""
        response = requests.get(f"{BASE_URL}/api/colores-catalogo", timeout=20)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Colores catalogo: {len(data)} colores")


class TestRegistroValidation:
    """Test registro state validation and force state"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token and find a test registro"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
            timeout=20
        )
        self.token = response.json().get("access_token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        # Get a registro for testing
        reg_response = requests.get(
            f"{BASE_URL}/api/registros?limit=1&offset=0",
            timeout=30
        )
        if reg_response.status_code == 200:
            data = reg_response.json()
            if data["items"]:
                self.test_registro_id = data["items"][0]["id"]
            else:
                self.test_registro_id = None
        else:
            self.test_registro_id = None
    
    def test_validar_cambio_estado(self):
        """Test POST /api/registros/{id}/validar-cambio-estado"""
        if not self.test_registro_id:
            pytest.skip("No registro available for testing")
        
        response = requests.post(
            f"{BASE_URL}/api/registros/{self.test_registro_id}/validar-cambio-estado",
            json={"nuevo_estado": "Corte"},
            headers=self.headers,
            timeout=20
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "permitido" in data
        print(f"✓ Validar cambio estado: permitido={data['permitido']}")
    
    def test_skip_validacion_toggle(self):
        """Test PUT /api/registros/{id}/skip-validacion"""
        if not self.test_registro_id:
            pytest.skip("No registro available for testing")
        
        # Get current state
        reg_response = requests.get(
            f"{BASE_URL}/api/registros/{self.test_registro_id}",
            timeout=20
        )
        current_skip = reg_response.json().get("skip_validacion_estado", False)
        
        # Toggle
        response = requests.put(
            f"{BASE_URL}/api/registros/{self.test_registro_id}/skip-validacion",
            json={"skip_validacion_estado": not current_skip},
            headers=self.headers,
            timeout=20
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        # Restore original
        requests.put(
            f"{BASE_URL}/api/registros/{self.test_registro_id}/skip-validacion",
            json={"skip_validacion_estado": current_skip},
            headers=self.headers,
            timeout=20
        )
        print(f"✓ Skip validacion toggle works")


class TestDashboard:
    """Dashboard endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
            timeout=20
        )
        self.token = response.json().get("access_token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_dashboard_stats(self):
        """Test dashboard stats endpoint if exists"""
        # Try common dashboard endpoints
        endpoints = [
            "/api/dashboard/stats",
            "/api/stats",
            "/api/registros-estados"
        ]
        
        for endpoint in endpoints:
            response = requests.get(
                f"{BASE_URL}{endpoint}",
                headers=self.headers,
                timeout=20
            )
            if response.status_code == 200:
                print(f"✓ Dashboard endpoint {endpoint} works")
                return
        
        # At minimum, registros-estados should work
        response = requests.get(f"{BASE_URL}/api/registros-estados", timeout=20)
        assert response.status_code == 200
        print("✓ Dashboard data available via registros-estados")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
