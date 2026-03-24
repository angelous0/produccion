"""
Test Suite: Reportes de Producción P0
Tests for all 9 report endpoints:
1. Dashboard KPIs
2. Producción en Proceso
3. WIP por Etapa
4. Lotes Atrasados
5. Trazabilidad
6. Cumplimiento de Ruta
7. Balance por Terceros
8. Lotes Fraccionados
9. Filtros
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestReportesProduccionAuth:
    """Test authentication for reportes endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "eduard",
            "password": "eduard123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        return data["access_token"]
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get headers with auth token"""
        return {"Authorization": f"Bearer {auth_token}"}
    
    def test_dashboard_requires_auth(self):
        """Dashboard endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/reportes-produccion/dashboard")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    def test_en_proceso_requires_auth(self):
        """En proceso endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/reportes-produccion/en-proceso")
        assert response.status_code == 401
    
    def test_wip_etapa_requires_auth(self):
        """WIP etapa endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/reportes-produccion/wip-etapa")
        assert response.status_code == 401
    
    def test_atrasados_requires_auth(self):
        """Atrasados endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/reportes-produccion/atrasados")
        assert response.status_code == 401
    
    def test_filtros_requires_auth(self):
        """Filtros endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/reportes-produccion/filtros")
        assert response.status_code == 401


class TestDashboardKPIs:
    """Test Dashboard KPIs endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "eduard",
            "password": "eduard123"
        })
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_dashboard_returns_200(self, auth_headers):
        """Dashboard endpoint returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/dashboard",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_dashboard_has_required_fields(self, auth_headers):
        """Dashboard returns all required KPI fields"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/dashboard",
            headers=auth_headers
        )
        data = response.json()
        
        # Check required fields
        required_fields = [
            "total_en_proceso",
            "total_prendas_proceso",
            "atrasados",
            "movimientos_abiertos",
            "lotes_fraccionados",
            "distribucion_estado_op",
            "distribucion_estado",
            "por_servicio"
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
    
    def test_dashboard_kpi_types(self, auth_headers):
        """Dashboard KPIs have correct types"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/dashboard",
            headers=auth_headers
        )
        data = response.json()
        
        # Numeric fields
        assert isinstance(data["total_en_proceso"], int)
        assert isinstance(data["total_prendas_proceso"], int)
        assert isinstance(data["atrasados"], int)
        assert isinstance(data["movimientos_abiertos"], int)
        assert isinstance(data["lotes_fraccionados"], int)
        
        # Array fields
        assert isinstance(data["distribucion_estado_op"], list)
        assert isinstance(data["distribucion_estado"], list)
        assert isinstance(data["por_servicio"], list)
    
    def test_dashboard_distribucion_estado_op_structure(self, auth_headers):
        """Distribucion estado_op has correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/dashboard",
            headers=auth_headers
        )
        data = response.json()
        
        for item in data["distribucion_estado_op"]:
            assert "estado_op" in item
            assert "cantidad" in item
            assert "prendas" in item
            assert isinstance(item["cantidad"], int)
            assert isinstance(item["prendas"], int)
    
    def test_dashboard_por_servicio_structure(self, auth_headers):
        """Por servicio has correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/dashboard",
            headers=auth_headers
        )
        data = response.json()
        
        for item in data["por_servicio"]:
            assert "servicio" in item
            assert "lotes" in item
            assert "enviadas" in item
            assert "recibidas" in item


class TestProduccionEnProceso:
    """Test Producción en Proceso endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "eduard",
            "password": "eduard123"
        })
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_en_proceso_returns_200(self, auth_headers):
        """En proceso endpoint returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/en-proceso",
            headers=auth_headers
        )
        assert response.status_code == 200
    
    def test_en_proceso_has_registros_and_total(self, auth_headers):
        """En proceso returns registros array and total"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/en-proceso",
            headers=auth_headers
        )
        data = response.json()
        
        assert "registros" in data
        assert "total" in data
        assert isinstance(data["registros"], list)
        assert isinstance(data["total"], int)
        assert data["total"] == len(data["registros"])
    
    def test_en_proceso_registro_structure(self, auth_headers):
        """En proceso registros have correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/en-proceso",
            headers=auth_headers
        )
        data = response.json()
        
        if data["registros"]:
            reg = data["registros"][0]
            required_fields = [
                "id", "n_corte", "estado", "estado_op",
                "total_prendas", "dias_proceso",
                "total_movimientos", "movimientos_cerrados"
            ]
            for field in required_fields:
                assert field in reg, f"Missing field: {field}"
    
    def test_en_proceso_filter_by_estado(self, auth_headers):
        """En proceso can filter by estado"""
        # First get all to find a valid estado
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/en-proceso",
            headers=auth_headers
        )
        data = response.json()
        
        if data["registros"]:
            estado = data["registros"][0]["estado"]
            
            # Filter by that estado
            response2 = requests.get(
                f"{BASE_URL}/api/reportes-produccion/en-proceso?estado={estado}",
                headers=auth_headers
            )
            data2 = response2.json()
            
            # All results should have that estado
            for reg in data2["registros"]:
                assert reg["estado"] == estado


class TestWIPEtapa:
    """Test WIP por Etapa endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "eduard",
            "password": "eduard123"
        })
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_wip_etapa_returns_200(self, auth_headers):
        """WIP etapa endpoint returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/wip-etapa",
            headers=auth_headers
        )
        assert response.status_code == 200
    
    def test_wip_etapa_has_etapas_and_total(self, auth_headers):
        """WIP etapa returns etapas array and total_etapas"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/wip-etapa",
            headers=auth_headers
        )
        data = response.json()
        
        assert "etapas" in data
        assert "total_etapas" in data
        assert isinstance(data["etapas"], list)
        assert data["total_etapas"] == len(data["etapas"])
    
    def test_wip_etapa_structure(self, auth_headers):
        """WIP etapa items have correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/wip-etapa",
            headers=auth_headers
        )
        data = response.json()
        
        if data["etapas"]:
            etapa = data["etapas"][0]
            required_fields = ["etapa", "lotes", "prendas", "urgentes"]
            for field in required_fields:
                assert field in etapa, f"Missing field: {field}"
            
            assert isinstance(etapa["lotes"], int)
            assert isinstance(etapa["prendas"], int)
            assert isinstance(etapa["urgentes"], int)


class TestLotesAtrasados:
    """Test Lotes Atrasados endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "eduard",
            "password": "eduard123"
        })
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_atrasados_returns_200(self, auth_headers):
        """Atrasados endpoint returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/atrasados",
            headers=auth_headers
        )
        assert response.status_code == 200
    
    def test_atrasados_has_registros_and_total(self, auth_headers):
        """Atrasados returns registros array and total"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/atrasados",
            headers=auth_headers
        )
        data = response.json()
        
        assert "registros" in data
        assert "total" in data
        assert isinstance(data["registros"], list)
    
    def test_atrasados_registro_structure(self, auth_headers):
        """Atrasados registros have correct structure with atraso info"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/atrasados",
            headers=auth_headers
        )
        data = response.json()
        
        if data["registros"]:
            reg = data["registros"][0]
            required_fields = [
                "id", "n_corte", "estado", "total_prendas",
                "dias_proceso", "entrega_vencida", "movs_vencidos",
                "dias_atraso_entrega"
            ]
            for field in required_fields:
                assert field in reg, f"Missing field: {field}"


class TestTrazabilidad:
    """Test Trazabilidad endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "eduard",
            "password": "eduard123"
        })
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.fixture(scope="class")
    def valid_registro_id(self, auth_headers):
        """Get a valid registro ID for testing"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/en-proceso",
            headers=auth_headers
        )
        data = response.json()
        if data["registros"]:
            return data["registros"][0]["id"]
        return None
    
    def test_trazabilidad_returns_404_for_invalid_id(self, auth_headers):
        """Trazabilidad returns 404 for non-existent registro"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/trazabilidad/non-existent-id",
            headers=auth_headers
        )
        assert response.status_code == 404
    
    def test_trazabilidad_returns_200_for_valid_id(self, auth_headers, valid_registro_id):
        """Trazabilidad returns 200 for valid registro"""
        if not valid_registro_id:
            pytest.skip("No registros available for testing")
        
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/trazabilidad/{valid_registro_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
    
    def test_trazabilidad_has_required_fields(self, auth_headers, valid_registro_id):
        """Trazabilidad returns registro, movimientos, divisiones"""
        if not valid_registro_id:
            pytest.skip("No registros available for testing")
        
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/trazabilidad/{valid_registro_id}",
            headers=auth_headers
        )
        data = response.json()
        
        assert "registro" in data
        assert "movimientos" in data
        assert "divisiones" in data
        assert "total_movimientos" in data
        
        # Registro should have key fields
        reg = data["registro"]
        assert "id" in reg
        assert "n_corte" in reg
        assert "estado" in reg
        assert "total_prendas" in reg
    
    def test_trazabilidad_movimientos_structure(self, auth_headers, valid_registro_id):
        """Trazabilidad movimientos have correct structure"""
        if not valid_registro_id:
            pytest.skip("No registros available for testing")
        
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/trazabilidad/{valid_registro_id}",
            headers=auth_headers
        )
        data = response.json()
        
        if data["movimientos"]:
            mov = data["movimientos"][0]
            required_fields = [
                "id", "servicio_nombre", "persona_nombre",
                "cantidad_enviada", "cantidad_recibida"
            ]
            for field in required_fields:
                assert field in mov, f"Missing field in movimiento: {field}"


class TestCumplimientoRuta:
    """Test Cumplimiento de Ruta endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "eduard",
            "password": "eduard123"
        })
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_cumplimiento_ruta_returns_200(self, auth_headers):
        """Cumplimiento ruta endpoint returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/cumplimiento-ruta",
            headers=auth_headers
        )
        assert response.status_code == 200
    
    def test_cumplimiento_ruta_has_registros_and_total(self, auth_headers):
        """Cumplimiento ruta returns registros array and total"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/cumplimiento-ruta",
            headers=auth_headers
        )
        data = response.json()
        
        assert "registros" in data
        assert "total" in data
        assert isinstance(data["registros"], list)
    
    def test_cumplimiento_ruta_registro_structure(self, auth_headers):
        """Cumplimiento ruta registros have compliance info"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/cumplimiento-ruta",
            headers=auth_headers
        )
        data = response.json()
        
        if data["registros"]:
            reg = data["registros"][0]
            required_fields = [
                "id", "n_corte", "ruta_nombre",
                "total_etapas", "completadas", "en_curso", "pendientes",
                "pct_cumplimiento", "detalle_etapas"
            ]
            for field in required_fields:
                assert field in reg, f"Missing field: {field}"
            
            # Check detalle_etapas structure
            if reg["detalle_etapas"]:
                etapa = reg["detalle_etapas"][0]
                assert "nombre" in etapa
                assert "estado" in etapa
                assert etapa["estado"] in ["COMPLETADA", "EN_CURSO", "PENDIENTE"]


class TestBalanceTerceros:
    """Test Balance por Terceros endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "eduard",
            "password": "eduard123"
        })
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_balance_terceros_returns_200(self, auth_headers):
        """Balance terceros endpoint returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/balance-terceros",
            headers=auth_headers
        )
        assert response.status_code == 200
    
    def test_balance_terceros_has_balance_and_resumen(self, auth_headers):
        """Balance terceros returns balance array and resumen_servicio"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/balance-terceros",
            headers=auth_headers
        )
        data = response.json()
        
        assert "balance" in data
        assert "resumen_servicio" in data
        assert "total" in data
        assert isinstance(data["balance"], list)
        assert isinstance(data["resumen_servicio"], dict)
    
    def test_balance_terceros_balance_structure(self, auth_headers):
        """Balance terceros balance items have correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/balance-terceros",
            headers=auth_headers
        )
        data = response.json()
        
        if data["balance"]:
            item = data["balance"][0]
            required_fields = [
                "servicio", "persona", "lotes",
                "total_enviadas", "total_recibidas", "total_diferencia",
                "costo_total", "movs_abiertos", "prendas_en_poder"
            ]
            for field in required_fields:
                assert field in item, f"Missing field: {field}"


class TestLotesFraccionados:
    """Test Lotes Fraccionados endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "eduard",
            "password": "eduard123"
        })
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_lotes_fraccionados_returns_200(self, auth_headers):
        """Lotes fraccionados endpoint returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/lotes-fraccionados",
            headers=auth_headers
        )
        assert response.status_code == 200
    
    def test_lotes_fraccionados_has_familias_and_total(self, auth_headers):
        """Lotes fraccionados returns familias array and total"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/lotes-fraccionados",
            headers=auth_headers
        )
        data = response.json()
        
        assert "familias" in data
        assert "total" in data
        assert isinstance(data["familias"], list)
    
    def test_lotes_fraccionados_familia_structure(self, auth_headers):
        """Lotes fraccionados familias have correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/lotes-fraccionados",
            headers=auth_headers
        )
        data = response.json()
        
        if data["familias"]:
            familia = data["familias"][0]
            required_fields = [
                "padre_id", "padre_corte", "padre_estado",
                "padre_prendas", "hijos", "total_hijos",
                "total_hijos_prendas", "total_familia_prendas"
            ]
            for field in required_fields:
                assert field in familia, f"Missing field: {field}"
            
            # Check hijos structure
            if familia["hijos"]:
                hijo = familia["hijos"][0]
                assert "id" in hijo
                assert "n_corte" in hijo
                assert "estado" in hijo


class TestFiltros:
    """Test Filtros endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "eduard",
            "password": "eduard123"
        })
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_filtros_returns_200(self, auth_headers):
        """Filtros endpoint returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/filtros",
            headers=auth_headers
        )
        assert response.status_code == 200
    
    def test_filtros_has_all_filter_options(self, auth_headers):
        """Filtros returns servicios, rutas, modelos, estados"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/filtros",
            headers=auth_headers
        )
        data = response.json()
        
        assert "servicios" in data
        assert "rutas" in data
        assert "modelos" in data
        assert "estados" in data
        
        assert isinstance(data["servicios"], list)
        assert isinstance(data["rutas"], list)
        assert isinstance(data["modelos"], list)
        assert isinstance(data["estados"], list)
    
    def test_filtros_servicios_structure(self, auth_headers):
        """Filtros servicios have id and nombre"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/filtros",
            headers=auth_headers
        )
        data = response.json()
        
        if data["servicios"]:
            srv = data["servicios"][0]
            assert "id" in srv
            assert "nombre" in srv
    
    def test_filtros_rutas_structure(self, auth_headers):
        """Filtros rutas have id and nombre"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/filtros",
            headers=auth_headers
        )
        data = response.json()
        
        if data["rutas"]:
            ruta = data["rutas"][0]
            assert "id" in ruta
            assert "nombre" in ruta


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
