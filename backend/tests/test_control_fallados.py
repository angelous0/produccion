"""
Test: Control de Fallados - Pantalla centralizada operativa diaria
Endpoint: GET /api/fallados-control
Features: KPIs, filtros por estado/servicio/persona/fecha/vencidos/pendientes/linea_negocio
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://kardex-pt-sync.preview.emergentagent.com').rstrip('/')

@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username": "eduard",
        "password": "eduard123"
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["access_token"]

@pytest.fixture
def headers(auth_token):
    """Headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestFalladosControlEndpoint:
    """Tests for GET /api/fallados-control endpoint"""
    
    def test_get_fallados_control_basic(self, headers):
        """Test basic endpoint returns registros with fallados + KPIs"""
        response = requests.get(f"{BASE_URL}/api/fallados-control", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "registros" in data
        assert "kpis" in data
        assert isinstance(data["registros"], list)
        assert isinstance(data["kpis"], dict)
        
        # Verify KPI structure
        kpis = data["kpis"]
        required_kpis = ["total_registros", "total_fallados", "total_pendiente", 
                        "total_vencidos", "total_recuperado", "total_liquidacion", 
                        "total_merma", "total_completados"]
        for kpi in required_kpis:
            assert kpi in kpis, f"Missing KPI: {kpi}"
            assert isinstance(kpis[kpi], int), f"KPI {kpi} should be int"
        
        print(f"✓ Basic endpoint works: {len(data['registros'])} registros, KPIs present")
    
    def test_registro_structure(self, headers):
        """Test each registro has required fields"""
        response = requests.get(f"{BASE_URL}/api/fallados-control", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        if len(data["registros"]) > 0:
            registro = data["registros"][0]
            required_fields = ["id", "n_corte", "estado_op", "modelo", "marca",
                             "total_fallados", "total_enviado", "recuperado",
                             "liquidacion", "merma_arreglos", "pendiente",
                             "sin_enviar", "arreglos_vencidos", "estado_control"]
            for field in required_fields:
                assert field in registro, f"Missing field: {field}"
            
            # Verify estado_control is valid
            valid_estados = ["VENCIDO", "PENDIENTE", "EN_PROCESO", "COMPLETADO"]
            assert registro["estado_control"] in valid_estados, f"Invalid estado_control: {registro['estado_control']}"
            
            print(f"✓ Registro structure valid: {registro['n_corte']} - {registro['estado_control']}")
    
    def test_filter_by_estado_pendiente(self, headers):
        """Test filter by estado=PENDIENTE"""
        response = requests.get(f"{BASE_URL}/api/fallados-control?estado=PENDIENTE", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        for registro in data["registros"]:
            assert registro["estado_control"] == "PENDIENTE", f"Expected PENDIENTE, got {registro['estado_control']}"
        
        print(f"✓ Filter estado=PENDIENTE: {len(data['registros'])} registros")
    
    def test_filter_by_estado_en_proceso(self, headers):
        """Test filter by estado=EN_PROCESO"""
        response = requests.get(f"{BASE_URL}/api/fallados-control?estado=EN_PROCESO", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        for registro in data["registros"]:
            assert registro["estado_control"] == "EN_PROCESO", f"Expected EN_PROCESO, got {registro['estado_control']}"
        
        print(f"✓ Filter estado=EN_PROCESO: {len(data['registros'])} registros")
    
    def test_filter_solo_vencidos(self, headers):
        """Test filter solo_vencidos=true returns only VENCIDO"""
        response = requests.get(f"{BASE_URL}/api/fallados-control?solo_vencidos=true", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        for registro in data["registros"]:
            assert registro["estado_control"] == "VENCIDO", f"Expected VENCIDO, got {registro['estado_control']}"
        
        print(f"✓ Filter solo_vencidos: {len(data['registros'])} registros")
    
    def test_filter_solo_pendientes(self, headers):
        """Test filter solo_pendientes=true returns PENDIENTE or EN_PROCESO"""
        response = requests.get(f"{BASE_URL}/api/fallados-control?solo_pendientes=true", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        valid_estados = ["PENDIENTE", "EN_PROCESO"]
        for registro in data["registros"]:
            assert registro["estado_control"] in valid_estados, f"Expected PENDIENTE/EN_PROCESO, got {registro['estado_control']}"
        
        print(f"✓ Filter solo_pendientes: {len(data['registros'])} registros")
    
    def test_kpis_calculation(self, headers):
        """Test KPIs are calculated correctly from registros"""
        response = requests.get(f"{BASE_URL}/api/fallados-control", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        registros = data["registros"]
        kpis = data["kpis"]
        
        # Verify total_registros
        assert kpis["total_registros"] == len(registros), "total_registros mismatch"
        
        # Verify total_fallados
        calc_total_fallados = sum(r["total_fallados"] for r in registros)
        assert kpis["total_fallados"] == calc_total_fallados, f"total_fallados mismatch: {kpis['total_fallados']} vs {calc_total_fallados}"
        
        # Verify total_pendiente
        calc_total_pendiente = sum(r["pendiente"] for r in registros)
        assert kpis["total_pendiente"] == calc_total_pendiente, f"total_pendiente mismatch"
        
        # Verify total_recuperado
        calc_total_recuperado = sum(r["recuperado"] for r in registros)
        assert kpis["total_recuperado"] == calc_total_recuperado, f"total_recuperado mismatch"
        
        # Verify total_vencidos (count of VENCIDO registros)
        calc_total_vencidos = len([r for r in registros if r["estado_control"] == "VENCIDO"])
        assert kpis["total_vencidos"] == calc_total_vencidos, f"total_vencidos mismatch"
        
        print(f"✓ KPIs calculation verified: fallados={kpis['total_fallados']}, pendiente={kpis['total_pendiente']}")
    
    def test_estado_consolidado_logic(self, headers):
        """Test estado_control logic: VENCIDO > EN_PROCESO > PENDIENTE > COMPLETADO"""
        response = requests.get(f"{BASE_URL}/api/fallados-control", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        for registro in data["registros"]:
            estado = registro["estado_control"]
            vencidos = registro["arreglos_vencidos"]
            pendiente = registro["pendiente"]
            total_enviado = registro["total_enviado"]
            total_fallados = registro["total_fallados"]
            
            # VENCIDO: tiene arreglos vencidos
            if vencidos > 0:
                assert estado == "VENCIDO", f"Registro {registro['n_corte']} should be VENCIDO (has {vencidos} vencidos)"
            # COMPLETADO: pendiente <= 0 y total_fallados > 0
            elif pendiente <= 0 and total_fallados > 0:
                assert estado == "COMPLETADO", f"Registro {registro['n_corte']} should be COMPLETADO"
            # EN_PROCESO: tiene envios
            elif total_enviado > 0:
                assert estado == "EN_PROCESO", f"Registro {registro['n_corte']} should be EN_PROCESO"
            # PENDIENTE: sin envios
            else:
                assert estado == "PENDIENTE", f"Registro {registro['n_corte']} should be PENDIENTE"
        
        print(f"✓ Estado consolidado logic verified for {len(data['registros'])} registros")
    
    def test_known_registros_present(self, headers):
        """Test known registros with fallados are present (008, 013, 007)"""
        response = requests.get(f"{BASE_URL}/api/fallados-control", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        n_cortes = [r["n_corte"] for r in data["registros"]]
        
        # These registros should have fallados according to test data
        expected_cortes = ["008", "013", "007"]
        for corte in expected_cortes:
            assert corte in n_cortes, f"Expected registro {corte} with fallados not found"
        
        print(f"✓ Known registros present: {expected_cortes}")
    
    def test_registro_008_data(self, headers):
        """Test specific data for registro 008 (15 fallados)"""
        response = requests.get(f"{BASE_URL}/api/fallados-control", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        reg_008 = next((r for r in data["registros"] if r["n_corte"] == "008"), None)
        
        assert reg_008 is not None, "Registro 008 not found"
        assert reg_008["total_fallados"] == 15, f"Expected 15 fallados, got {reg_008['total_fallados']}"
        
        print(f"✓ Registro 008: {reg_008['total_fallados']} fallados, estado={reg_008['estado_control']}")


class TestFalladosControlFilters:
    """Additional filter tests"""
    
    def test_filter_by_fecha_desde(self, headers):
        """Test filter by fecha_desde"""
        response = requests.get(f"{BASE_URL}/api/fallados-control?fecha_desde=2026-01-01", headers=headers)
        assert response.status_code == 200
        print(f"✓ Filter fecha_desde works: {len(response.json()['registros'])} registros")
    
    def test_filter_by_fecha_hasta(self, headers):
        """Test filter by fecha_hasta"""
        response = requests.get(f"{BASE_URL}/api/fallados-control?fecha_hasta=2026-12-31", headers=headers)
        assert response.status_code == 200
        print(f"✓ Filter fecha_hasta works: {len(response.json()['registros'])} registros")
    
    def test_combined_filters(self, headers):
        """Test multiple filters combined"""
        response = requests.get(
            f"{BASE_URL}/api/fallados-control?solo_pendientes=true&fecha_desde=2026-01-01",
            headers=headers
        )
        assert response.status_code == 200
        
        data = response.json()
        valid_estados = ["PENDIENTE", "EN_PROCESO"]
        for registro in data["registros"]:
            assert registro["estado_control"] in valid_estados
        
        print(f"✓ Combined filters work: {len(data['registros'])} registros")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
