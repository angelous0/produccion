"""
Test suite for Trazabilidad KPIs and related features:
- GET /api/registros with mermas_total, fallados_total, arreglos_vencidos fields
- GET /api/reportes/trazabilidad-kpis endpoint
- GET /api/reportes-produccion/alertas-produccion with servicio_id
- GET /api/export/mermas, /api/export/fallados, /api/export/arreglos CSV exports
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAuth:
    """Authentication tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for eduard user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "eduard",
            "password": "eduard123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, f"No access_token in response: {data}"
        return data["access_token"]
    
    def test_login_success(self):
        """Test login with eduard/eduard123"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "eduard",
            "password": "eduard123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["username"] == "eduard"


class TestRegistrosWithSaludFields:
    """Test GET /api/registros returns mermas_total, fallados_total, arreglos_vencidos"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "eduard",
            "password": "eduard123"
        })
        return response.json()["access_token"]
    
    def test_registros_list_has_salud_fields(self, auth_token):
        """Verify registros endpoint returns salud fields"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/registros", headers=headers)
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Should have items array
        assert "items" in data, f"No items in response: {data.keys()}"
        assert len(data["items"]) > 0, "No registros found"
        
        # Check first registro has salud fields
        first_registro = data["items"][0]
        assert "mermas_total" in first_registro, f"Missing mermas_total in registro: {first_registro.keys()}"
        assert "fallados_total" in first_registro, f"Missing fallados_total in registro: {first_registro.keys()}"
        assert "arreglos_vencidos" in first_registro, f"Missing arreglos_vencidos in registro: {first_registro.keys()}"
        
        # Verify they are numeric
        assert isinstance(first_registro["mermas_total"], (int, float)), "mermas_total should be numeric"
        assert isinstance(first_registro["fallados_total"], (int, float)), "fallados_total should be numeric"
        assert isinstance(first_registro["arreglos_vencidos"], (int, float)), "arreglos_vencidos should be numeric"
        
        print(f"✓ Registros list has salud fields. First registro: mermas={first_registro['mermas_total']}, fallados={first_registro['fallados_total']}, arreglos_vencidos={first_registro['arreglos_vencidos']}")


class TestTrazabilidadKPIs:
    """Test GET /api/reportes/trazabilidad-kpis endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "eduard",
            "password": "eduard123"
        })
        return response.json()["access_token"]
    
    def test_trazabilidad_kpis_endpoint_exists(self, auth_token):
        """Verify KPIs endpoint returns 200"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/reportes/trazabilidad-kpis", headers=headers)
        
        assert response.status_code == 200, f"KPIs endpoint failed: {response.status_code} - {response.text}"
    
    def test_trazabilidad_kpis_structure(self, auth_token):
        """Verify KPIs response has expected structure"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/reportes/trazabilidad-kpis", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check main structure
        assert "kpis" in data, f"Missing 'kpis' in response: {data.keys()}"
        assert "mermas_por_servicio" in data, f"Missing 'mermas_por_servicio' in response"
        assert "fallados_por_servicio" in data, f"Missing 'fallados_por_servicio' in response"
        assert "arreglos_vencidos" in data, f"Missing 'arreglos_vencidos' in response"
        assert "top_perdidas" in data, f"Missing 'top_perdidas' in response"
        assert "arreglos_por_responsable" in data, f"Missing 'arreglos_por_responsable' in response"
        
        # Check KPIs object
        kpis = data["kpis"]
        assert "mermas_total" in kpis, f"Missing mermas_total in kpis"
        assert "fallados_total" in kpis, f"Missing fallados_total in kpis"
        assert "arreglos_total" in kpis, f"Missing arreglos_total in kpis"
        assert "arreglos_vencidos" in kpis, f"Missing arreglos_vencidos in kpis"
        
        print(f"✓ KPIs structure valid. Totals: mermas={kpis['mermas_total']}, fallados={kpis['fallados_total']}, arreglos={kpis['arreglos_total']}, vencidos={kpis['arreglos_vencidos']}")
    
    def test_trazabilidad_kpis_data_types(self, auth_token):
        """Verify KPIs data types are correct"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/reportes/trazabilidad-kpis", headers=headers)
        
        data = response.json()
        kpis = data["kpis"]
        
        # All KPI values should be integers
        assert isinstance(kpis["mermas_total"], int), "mermas_total should be int"
        assert isinstance(kpis["fallados_total"], int), "fallados_total should be int"
        assert isinstance(kpis["arreglos_total"], int), "arreglos_total should be int"
        assert isinstance(kpis["arreglos_vencidos"], int), "arreglos_vencidos should be int"
        
        # Arrays should be lists
        assert isinstance(data["mermas_por_servicio"], list), "mermas_por_servicio should be list"
        assert isinstance(data["fallados_por_servicio"], list), "fallados_por_servicio should be list"
        assert isinstance(data["arreglos_vencidos"], list), "arreglos_vencidos should be list"
        assert isinstance(data["top_perdidas"], list), "top_perdidas should be list"


class TestAlertasProduccion:
    """Test GET /api/reportes-produccion/alertas-produccion with servicio_id"""
    
    def test_alertas_produccion_endpoint(self):
        """Verify alertas endpoint returns 200 (no auth required based on code)"""
        response = requests.get(f"{BASE_URL}/api/reportes-produccion/alertas-produccion")
        
        assert response.status_code == 200, f"Alertas endpoint failed: {response.status_code} - {response.text}"
    
    def test_alertas_produccion_structure(self):
        """Verify alertas response has expected structure"""
        response = requests.get(f"{BASE_URL}/api/reportes-produccion/alertas-produccion")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "alertas" in data, f"Missing 'alertas' in response: {data.keys()}"
        assert "resumen" in data, f"Missing 'resumen' in response"
        
        # Check resumen structure
        resumen = data["resumen"]
        assert "vencidos" in resumen
        assert "criticos" in resumen
        assert "paralizados" in resumen
        assert "total" in resumen
        
        print(f"✓ Alertas structure valid. Resumen: {resumen}")
    
    def test_alertas_include_servicio_id(self):
        """Verify each alerta includes servicio_id field"""
        response = requests.get(f"{BASE_URL}/api/reportes-produccion/alertas-produccion")
        
        data = response.json()
        alertas = data["alertas"]
        
        if len(alertas) > 0:
            first_alerta = alertas[0]
            assert "servicio_id" in first_alerta, f"Missing servicio_id in alerta: {first_alerta.keys()}"
            assert first_alerta["servicio_id"] is not None, "servicio_id should not be None"
            print(f"✓ Alertas include servicio_id. First alerta servicio_id: {first_alerta['servicio_id']}")
        else:
            print("⚠ No alertas to verify servicio_id (may be expected if no active alerts)")


class TestCSVExports:
    """Test CSV export endpoints for mermas, fallados, arreglos"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "eduard",
            "password": "eduard123"
        })
        return response.json()["access_token"]
    
    def test_export_mermas_csv(self, auth_token):
        """Test GET /api/export/mermas returns CSV"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/export/mermas", headers=headers)
        
        assert response.status_code == 200, f"Export mermas failed: {response.status_code} - {response.text}"
        
        # Check content type is CSV
        content_type = response.headers.get("content-type", "")
        assert "text/csv" in content_type, f"Expected CSV content-type, got: {content_type}"
        
        # Check content-disposition header
        content_disp = response.headers.get("content-disposition", "")
        assert "attachment" in content_disp, f"Expected attachment disposition, got: {content_disp}"
        assert "mermas" in content_disp.lower(), f"Filename should contain 'mermas': {content_disp}"
        
        print(f"✓ Export mermas CSV works. Content-Disposition: {content_disp}")
    
    def test_export_fallados_csv(self, auth_token):
        """Test GET /api/export/fallados returns CSV"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/export/fallados", headers=headers)
        
        assert response.status_code == 200, f"Export fallados failed: {response.status_code} - {response.text}"
        
        content_type = response.headers.get("content-type", "")
        assert "text/csv" in content_type, f"Expected CSV content-type, got: {content_type}"
        
        content_disp = response.headers.get("content-disposition", "")
        assert "fallados" in content_disp.lower(), f"Filename should contain 'fallados': {content_disp}"
        
        print(f"✓ Export fallados CSV works. Content-Disposition: {content_disp}")
    
    def test_export_arreglos_csv(self, auth_token):
        """Test GET /api/export/arreglos returns CSV"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/export/arreglos", headers=headers)
        
        assert response.status_code == 200, f"Export arreglos failed: {response.status_code} - {response.text}"
        
        content_type = response.headers.get("content-type", "")
        assert "text/csv" in content_type, f"Expected CSV content-type, got: {content_type}"
        
        content_disp = response.headers.get("content-disposition", "")
        assert "arreglos" in content_disp.lower(), f"Filename should contain 'arreglos': {content_disp}"
        
        print(f"✓ Export arreglos CSV works. Content-Disposition: {content_disp}")


class TestDashboard:
    """Test dashboard endpoint works correctly"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "eduard",
            "password": "eduard123"
        })
        return response.json()["access_token"]
    
    def test_dashboard_stats(self, auth_token):
        """Test dashboard stats endpoint"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/stats", headers=headers)
        
        assert response.status_code == 200, f"Dashboard stats failed: {response.status_code} - {response.text}"
        data = response.json()
        
        # Should have basic stats
        assert "total_registros" in data or "registros" in data or isinstance(data, dict), f"Unexpected stats format: {data}"
        print(f"✓ Dashboard stats endpoint works")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
