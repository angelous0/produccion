"""
Backend Tests for Valorización APIs (MP, WIP, PT)
Tests: costos servicio, cierre, reportes valorizacion, empresas
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://textile-production-2.preview.emergentagent.com')
EMPRESA_ID = 6
TEST_REGISTRO_ID = "83fb4c4b-e4ef-459b-bf07-20f24a555123"

@pytest.fixture(scope="module")
def auth_token():
    """Login and get token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username": "eduard",
        "password": "eduard123"
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    data = response.json()
    assert "access_token" in data
    return data["access_token"]

@pytest.fixture
def auth_headers(auth_token):
    """Headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


class TestAuthentication:
    """Test authentication flow"""
    
    def test_login_success(self):
        """Test login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "eduard",
            "password": "eduard123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["username"] == "eduard"
    
    def test_login_invalid(self):
        """Test login with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "invalid",
            "password": "wrong"
        })
        assert response.status_code == 401


class TestEmpresas:
    """Test empresas endpoint"""
    
    def test_get_empresas(self, auth_headers):
        """GET /api/empresas - should return empresa id=6"""
        response = requests.get(f"{BASE_URL}/api/empresas", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Find empresa id=6
        empresa_6 = next((e for e in data if e.get("id") == 6), None)
        assert empresa_6 is not None, "Empresa id=6 not found"
        print(f"Found empresa 6: {empresa_6.get('nombre')}")


class TestReporteMPValorizado:
    """Test Inventario MP Valorizado report"""
    
    def test_get_mp_valorizado(self, auth_headers):
        """GET /api/reportes/inventario-mp-valorizado?empresa_id=6"""
        response = requests.get(
            f"{BASE_URL}/api/reportes/inventario-mp-valorizado?empresa_id={EMPRESA_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check structure
        assert "items" in data
        assert "resumen" in data
        assert "total_items" in data["resumen"]
        assert "total_valor" in data["resumen"]
        
        # Check items have required fields
        if len(data["items"]) > 0:
            item = data["items"][0]
            assert "id" in item
            assert "codigo" in item
            assert "nombre" in item
            assert "stock_actual" in item
            assert "valor_stock" in item
            assert "costo_promedio" in item
            assert "reservado" in item
            assert "disponible" in item
        
        print(f"MP Valorizado: {data['resumen']['total_items']} items, Total valor: S/ {data['resumen']['total_valor']}")


class TestReporteWIP:
    """Test WIP (Work in Process) report"""
    
    def test_get_wip(self, auth_headers):
        """GET /api/reportes/wip?empresa_id=6"""
        response = requests.get(
            f"{BASE_URL}/api/reportes/wip?empresa_id={EMPRESA_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check structure
        assert "registros" in data
        assert "resumen" in data
        assert "total_registros" in data["resumen"]
        assert "total_wip" in data["resumen"]
        
        # Check registro structure if any
        if len(data["registros"]) > 0:
            reg = data["registros"][0]
            assert "id" in reg
            assert "n_corte" in reg
            assert "estado" in reg
            assert "costo_mp" in reg
            assert "costo_servicios" in reg
            assert "costo_total" in reg
            assert "total_prendas" in reg
        
        print(f"WIP: {data['resumen']['total_registros']} registros en proceso, Total: S/ {data['resumen']['total_wip']}")


class TestReportePTValorizado:
    """Test PT (Producto Terminado) Valorizado report"""
    
    def test_get_pt_valorizado(self, auth_headers):
        """GET /api/reportes/inventario-pt-valorizado?empresa_id=6"""
        response = requests.get(
            f"{BASE_URL}/api/reportes/inventario-pt-valorizado?empresa_id={EMPRESA_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check structure
        assert "items" in data
        assert "resumen" in data
        assert "total_items" in data["resumen"]
        assert "total_valor" in data["resumen"]
        
        # Check items have required fields
        if len(data["items"]) > 0:
            item = data["items"][0]
            assert "id" in item
            assert "codigo" in item
            assert "nombre" in item
            assert "stock_actual" in item
            assert "valor_stock" in item
            assert "costo_promedio" in item
            assert "ops_cerradas" in item
        
        print(f"PT Valorizado: {data['resumen']['total_items']} items PT, Total valor: S/ {data['resumen']['total_valor']}")


class TestCostosServicio:
    """Test CRUD for costos servicio"""
    
    def test_get_costos_servicio(self, auth_headers):
        """GET /api/registros/{id}/costos-servicio"""
        response = requests.get(
            f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/costos-servicio",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check structure
        assert "costos" in data
        assert "total" in data
        assert isinstance(data["costos"], list)
        assert isinstance(data["total"], (int, float))
        
        print(f"Costos servicio: {len(data['costos'])} items, Total: S/ {data['total']}")
    
    def test_create_costo_servicio(self, auth_headers):
        """POST /api/registros/{id}/costos-servicio"""
        response = requests.post(
            f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/costos-servicio",
            headers=auth_headers,
            json={
                "empresa_id": EMPRESA_ID,
                "registro_id": TEST_REGISTRO_ID,
                "descripcion": "TEST Servicio de bordado",
                "monto": 50.0,
                "proveedor_texto": "Bordados Test SA"
            }
        )
        # May fail if registro is CERRADA, handle both cases
        if response.status_code == 400:
            assert "CERRADA" in response.text or "ANULADA" in response.text
            print("Registro is closed, cannot add costos (expected)")
        else:
            assert response.status_code == 200
            data = response.json()
            assert "id" in data
            assert data["descripcion"] == "TEST Servicio de bordado"
            assert data["monto"] == 50.0
            
            # Cleanup - delete the test costo
            costo_id = data["id"]
            del_response = requests.delete(
                f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/costos-servicio/{costo_id}",
                headers=auth_headers
            )
            print(f"Created and deleted test costo: {costo_id}")


class TestPreviewCierre:
    """Test cierre preview endpoint"""
    
    def test_get_preview_cierre(self, auth_headers):
        """GET /api/registros/{id}/preview-cierre"""
        response = requests.get(
            f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/preview-cierre",
            headers=auth_headers
        )
        
        # May return 400 if already closed
        if response.status_code == 400:
            assert "cierre registrado" in response.text.lower() or "ya tiene" in response.text.lower()
            print("Registro already has cierre (expected for closed OPs)")
        else:
            assert response.status_code == 200
            data = response.json()
            
            # Check structure
            assert "registro_id" in data
            assert "n_corte" in data
            assert "estado" in data
            assert "qty_terminada" in data
            assert "costo_mp" in data
            assert "costo_servicios" in data
            assert "costo_total" in data
            assert "costo_unit_pt" in data
            assert "puede_cerrar" in data
            
            print(f"Preview cierre: qty={data['qty_terminada']}, costo_mp={data['costo_mp']}, costo_serv={data['costo_servicios']}, puede_cerrar={data['puede_cerrar']}")


class TestPtItemAssignment:
    """Test PT item assignment to registro"""
    
    def test_update_pt_item(self, auth_headers):
        """PUT /api/registros/{id}/pt-item"""
        # Try to assign a PT item (may fail if closed)
        response = requests.put(
            f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/pt-item",
            headers=auth_headers,
            json={"pt_item_id": None}  # Just testing the endpoint works
        )
        
        if response.status_code == 400:
            assert "cerrada" in response.text.lower() or "anulada" in response.text.lower()
            print("Cannot modify pt_item on closed/anulada OP (expected)")
        else:
            assert response.status_code == 200
            print("PT item assignment endpoint working")


class TestGetCierre:
    """Test get cierre data"""
    
    def test_get_cierre_produccion(self, auth_headers):
        """GET /api/registros/{id}/cierre-produccion"""
        response = requests.get(
            f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/cierre-produccion",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # May be None if not closed
        if data is not None:
            assert "registro_id" in data
            assert "fecha" in data
            assert "qty_terminada" in data
            assert "costo_mp" in data
            assert "costo_servicios" in data
            assert "costo_total" in data
            assert "costo_unit_pt" in data
            print(f"Cierre found: qty={data['qty_terminada']}, costo_total={data['costo_total']}")
        else:
            print("No cierre yet for this registro")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
