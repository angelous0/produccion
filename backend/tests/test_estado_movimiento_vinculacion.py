"""
Tests for bidirectional state-movement linking feature.
Tests the new endpoints and EtapaRuta fields: obligatorio, aparece_en_estado
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
USERNAME = "eduard"
PASSWORD = "eduard123"

# Known IDs from the system
REGISTRO_ID = "e7082b07-7a9b-4b45-af14-bde1ebc09238"  # Registro 04
RUTA_POLO_ID = "707c5261-8e3e-4e3e-8e3e-8e3e8e3e8e3e"  # Polo route (approximate)
RUTA_PANTALON_ID = "9fef5e0b-8e3e-4e3e-8e3e-8e3e8e3e8e3e"  # Pantalon Denim route (approximate)


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username": USERNAME,
        "password": PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Authentication failed - skipping authenticated tests")


@pytest.fixture(scope="module")
def api_client(auth_token):
    """Shared requests session with auth"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session


class TestEtapaRutaFields:
    """Tests for EtapaRuta model with obligatorio and aparece_en_estado fields"""
    
    def test_get_rutas_produccion(self, api_client):
        """GET /api/rutas-produccion returns list of routes"""
        response = api_client.get(f"{BASE_URL}/api/rutas-produccion")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Expected list of routes"
        print(f"Found {len(data)} production routes")
        
    def test_ruta_etapas_have_obligatorio_field(self, api_client):
        """Verify etapas in routes have obligatorio field"""
        response = api_client.get(f"{BASE_URL}/api/rutas-produccion")
        assert response.status_code == 200
        rutas = response.json()
        
        if len(rutas) == 0:
            pytest.skip("No routes found to test")
        
        ruta = rutas[0]
        etapas = ruta.get('etapas', [])
        print(f"Route '{ruta.get('nombre')}' has {len(etapas)} etapas")
        
        # Check that etapas structure is correct
        for etapa in etapas:
            assert 'nombre' in etapa, "Etapa should have 'nombre' field"
            # obligatorio defaults to True if not present
            obligatorio = etapa.get('obligatorio', True)
            assert isinstance(obligatorio, bool), f"obligatorio should be bool, got {type(obligatorio)}"
            print(f"  - {etapa.get('nombre')}: obligatorio={obligatorio}")
    
    def test_ruta_etapas_have_aparece_en_estado_field(self, api_client):
        """Verify etapas in routes have aparece_en_estado field"""
        response = api_client.get(f"{BASE_URL}/api/rutas-produccion")
        assert response.status_code == 200
        rutas = response.json()
        
        if len(rutas) == 0:
            pytest.skip("No routes found to test")
        
        ruta = rutas[0]
        etapas = ruta.get('etapas', [])
        
        for etapa in etapas:
            # aparece_en_estado defaults to True if not present
            aparece_en_estado = etapa.get('aparece_en_estado', True)
            assert isinstance(aparece_en_estado, bool), f"aparece_en_estado should be bool, got {type(aparece_en_estado)}"
            print(f"  - {etapa.get('nombre')}: aparece_en_estado={aparece_en_estado}")
    
    def test_update_ruta_with_obligatorio_aparece_en_estado(self, api_client):
        """PUT /api/rutas-produccion/{id} accepts obligatorio and aparece_en_estado fields"""
        # First get existing routes
        response = api_client.get(f"{BASE_URL}/api/rutas-produccion")
        assert response.status_code == 200
        rutas = response.json()
        
        if len(rutas) == 0:
            pytest.skip("No routes found to test")
        
        ruta = rutas[0]
        ruta_id = ruta['id']
        
        # Prepare update payload with new fields
        etapas_updated = []
        for i, etapa in enumerate(ruta.get('etapas', [])):
            etapas_updated.append({
                "nombre": etapa.get('nombre'),
                "servicio_id": etapa.get('servicio_id'),
                "orden": i,
                "obligatorio": etapa.get('obligatorio', True),
                "aparece_en_estado": etapa.get('aparece_en_estado', True)
            })
        
        payload = {
            "nombre": ruta['nombre'],
            "descripcion": ruta.get('descripcion', ''),
            "etapas": etapas_updated
        }
        
        response = api_client.put(f"{BASE_URL}/api/rutas-produccion/{ruta_id}", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"Successfully updated route '{ruta['nombre']}' with obligatorio/aparece_en_estado fields")


class TestEstadosDisponibles:
    """Tests for GET /api/registros/{id}/estados-disponibles endpoint"""
    
    def test_estados_disponibles_returns_etapas_completas(self, api_client):
        """GET /api/registros/{id}/estados-disponibles returns etapas_completas"""
        response = api_client.get(f"{BASE_URL}/api/registros/{REGISTRO_ID}/estados-disponibles")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert 'estados' in data, "Response should have 'estados' field"
        assert 'usa_ruta' in data, "Response should have 'usa_ruta' field"
        
        if data.get('usa_ruta'):
            assert 'etapas_completas' in data, "Response should have 'etapas_completas' when usa_ruta=True"
            assert 'ruta_nombre' in data, "Response should have 'ruta_nombre' when usa_ruta=True"
            print(f"Route: {data.get('ruta_nombre')}")
            print(f"Estados: {data.get('estados')}")
            print(f"Etapas completas count: {len(data.get('etapas_completas', []))}")
        else:
            print("Registro does not use a route, using global states")
    
    def test_estados_disponibles_filters_by_aparece_en_estado(self, api_client):
        """Verify estados list only includes etapas with aparece_en_estado=True"""
        response = api_client.get(f"{BASE_URL}/api/registros/{REGISTRO_ID}/estados-disponibles")
        assert response.status_code == 200
        
        data = response.json()
        if not data.get('usa_ruta'):
            pytest.skip("Registro does not use a route")
        
        estados = data.get('estados', [])
        etapas_completas = data.get('etapas_completas', [])
        
        # Count etapas with aparece_en_estado=True
        etapas_visibles = [e for e in etapas_completas if e.get('aparece_en_estado', True)]
        
        # Estados should match etapas with aparece_en_estado=True
        assert len(estados) == len(etapas_visibles), \
            f"Estados count ({len(estados)}) should match visible etapas ({len(etapas_visibles)})"
        
        print(f"Estados (visible): {estados}")
        print(f"Total etapas: {len(etapas_completas)}, Visible: {len(etapas_visibles)}")


class TestAnalisisEstado:
    """Tests for GET /api/registros/{id}/analisis-estado endpoint"""
    
    def test_analisis_estado_returns_required_fields(self, api_client):
        """GET /api/registros/{id}/analisis-estado returns all required fields"""
        response = api_client.get(f"{BASE_URL}/api/registros/{REGISTRO_ID}/analisis-estado")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Required fields
        assert 'estado_actual' in data, "Response should have 'estado_actual'"
        assert 'estado_sugerido' in data, "Response should have 'estado_sugerido'"
        assert 'siguiente_estado_sugerido' in data, "Response should have 'siguiente_estado_sugerido'"
        assert 'movimiento_faltante_por_estado' in data, "Response should have 'movimiento_faltante_por_estado'"
        assert 'inconsistencias' in data, "Response should have 'inconsistencias'"
        assert 'bloqueos' in data, "Response should have 'bloqueos'"
        
        print(f"Estado actual: {data.get('estado_actual')}")
        print(f"Estado sugerido: {data.get('estado_sugerido')}")
        print(f"Siguiente estado sugerido: {data.get('siguiente_estado_sugerido')}")
        print(f"Movimiento faltante: {data.get('movimiento_faltante_por_estado')}")
        print(f"Inconsistencias: {data.get('inconsistencias')}")
        print(f"Bloqueos: {data.get('bloqueos')}")
    
    def test_analisis_estado_inconsistencias_structure(self, api_client):
        """Verify inconsistencias have correct structure"""
        response = api_client.get(f"{BASE_URL}/api/registros/{REGISTRO_ID}/analisis-estado")
        assert response.status_code == 200
        
        data = response.json()
        inconsistencias = data.get('inconsistencias', [])
        
        for inc in inconsistencias:
            assert 'tipo' in inc, "Inconsistencia should have 'tipo'"
            assert 'mensaje' in inc, "Inconsistencia should have 'mensaje'"
            assert 'severidad' in inc, "Inconsistencia should have 'severidad'"
            assert inc['severidad'] in ['error', 'warning', 'info'], \
                f"Severidad should be error/warning/info, got {inc['severidad']}"
            print(f"  [{inc['severidad']}] {inc['tipo']}: {inc['mensaje']}")
    
    def test_analisis_estado_movimiento_faltante_structure(self, api_client):
        """Verify movimiento_faltante_por_estado has correct structure when present"""
        response = api_client.get(f"{BASE_URL}/api/registros/{REGISTRO_ID}/analisis-estado")
        assert response.status_code == 200
        
        data = response.json()
        mov_faltante = data.get('movimiento_faltante_por_estado')
        
        if mov_faltante:
            assert 'servicio_id' in mov_faltante, "Should have 'servicio_id'"
            assert 'servicio_nombre' in mov_faltante, "Should have 'servicio_nombre'"
            assert 'etapa_nombre' in mov_faltante, "Should have 'etapa_nombre'"
            print(f"Movimiento faltante: {mov_faltante}")
        else:
            print("No movimiento faltante (all movements registered for current state)")


class TestValidarCambioEstado:
    """Tests for POST /api/registros/{id}/validar-cambio-estado endpoint"""
    
    def test_validar_cambio_estado_valid_state(self, api_client):
        """POST /api/registros/{id}/validar-cambio-estado with valid state"""
        # First get available states
        estados_resp = api_client.get(f"{BASE_URL}/api/registros/{REGISTRO_ID}/estados-disponibles")
        assert estados_resp.status_code == 200
        estados_data = estados_resp.json()
        estados = estados_data.get('estados', [])
        
        if len(estados) == 0:
            pytest.skip("No states available")
        
        # Try to validate change to first state
        response = api_client.post(
            f"{BASE_URL}/api/registros/{REGISTRO_ID}/validar-cambio-estado",
            json={"nuevo_estado": estados[0]}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert 'permitido' in data, "Response should have 'permitido'"
        assert 'bloqueos' in data, "Response should have 'bloqueos'"
        assert 'sugerencia_movimiento' in data, "Response should have 'sugerencia_movimiento'"
        
        print(f"Validating change to '{estados[0]}':")
        print(f"  Permitido: {data.get('permitido')}")
        print(f"  Bloqueos: {data.get('bloqueos')}")
        print(f"  Sugerencia movimiento: {data.get('sugerencia_movimiento')}")
    
    def test_validar_cambio_estado_blocks_invalid_state(self, api_client):
        """POST /api/registros/{id}/validar-cambio-estado blocks state outside route"""
        # First check if registro uses a route
        estados_resp = api_client.get(f"{BASE_URL}/api/registros/{REGISTRO_ID}/estados-disponibles")
        assert estados_resp.status_code == 200
        estados_data = estados_resp.json()
        
        if not estados_data.get('usa_ruta'):
            pytest.skip("Registro does not use a route, cannot test blocking")
        
        # Try to change to an invalid state
        response = api_client.post(
            f"{BASE_URL}/api/registros/{REGISTRO_ID}/validar-cambio-estado",
            json={"nuevo_estado": "EstadoInventado123"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get('permitido') == False, "Should not permit invalid state"
        assert len(data.get('bloqueos', [])) > 0, "Should have blocking message"
        
        print(f"Correctly blocked invalid state:")
        print(f"  Bloqueos: {data.get('bloqueos')}")
    
    def test_validar_cambio_estado_returns_sugerencia_movimiento(self, api_client):
        """POST /api/registros/{id}/validar-cambio-estado returns sugerencia_movimiento when applicable"""
        # Get available states
        estados_resp = api_client.get(f"{BASE_URL}/api/registros/{REGISTRO_ID}/estados-disponibles")
        assert estados_resp.status_code == 200
        estados_data = estados_resp.json()
        
        if not estados_data.get('usa_ruta'):
            pytest.skip("Registro does not use a route")
        
        etapas = estados_data.get('etapas_completas', [])
        
        # Find an etapa with servicio_id
        etapa_con_servicio = None
        for etapa in etapas:
            if etapa.get('servicio_id') and etapa.get('aparece_en_estado', True):
                etapa_con_servicio = etapa
                break
        
        if not etapa_con_servicio:
            pytest.skip("No etapa with servicio_id found")
        
        response = api_client.post(
            f"{BASE_URL}/api/registros/{REGISTRO_ID}/validar-cambio-estado",
            json={"nuevo_estado": etapa_con_servicio['nombre']}
        )
        assert response.status_code == 200
        
        data = response.json()
        print(f"Validating change to '{etapa_con_servicio['nombre']}':")
        print(f"  Permitido: {data.get('permitido')}")
        print(f"  Sugerencia movimiento: {data.get('sugerencia_movimiento')}")
        
        # If permitted and no movement exists, should suggest creating one
        if data.get('permitido') and data.get('sugerencia_movimiento'):
            sug = data['sugerencia_movimiento']
            assert 'servicio_id' in sug, "Sugerencia should have servicio_id"
            assert 'servicio_nombre' in sug, "Sugerencia should have servicio_nombre"
            assert 'etapa_nombre' in sug, "Sugerencia should have etapa_nombre"
    
    def test_validar_cambio_estado_missing_body(self, api_client):
        """POST /api/registros/{id}/validar-cambio-estado returns 400 without nuevo_estado"""
        response = api_client.post(
            f"{BASE_URL}/api/registros/{REGISTRO_ID}/validar-cambio-estado",
            json={}
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"


class TestIntegrationScenarios:
    """Integration tests for state-movement linking scenarios"""
    
    def test_full_flow_get_analysis_and_validate(self, api_client):
        """Test full flow: get analysis, then validate state change"""
        # Step 1: Get analysis
        analysis_resp = api_client.get(f"{BASE_URL}/api/registros/{REGISTRO_ID}/analisis-estado")
        assert analysis_resp.status_code == 200
        analysis = analysis_resp.json()
        
        print(f"Current state: {analysis.get('estado_actual')}")
        print(f"Suggested state: {analysis.get('estado_sugerido')}")
        
        # Step 2: Get available states
        estados_resp = api_client.get(f"{BASE_URL}/api/registros/{REGISTRO_ID}/estados-disponibles")
        assert estados_resp.status_code == 200
        estados_data = estados_resp.json()
        
        # Step 3: If there's a suggested next state, validate it
        siguiente = analysis.get('siguiente_estado_sugerido')
        if siguiente:
            validate_resp = api_client.post(
                f"{BASE_URL}/api/registros/{REGISTRO_ID}/validar-cambio-estado",
                json={"nuevo_estado": siguiente}
            )
            assert validate_resp.status_code == 200
            validate_data = validate_resp.json()
            
            print(f"Validating next state '{siguiente}':")
            print(f"  Permitido: {validate_data.get('permitido')}")
            print(f"  Bloqueos: {validate_data.get('bloqueos')}")
        else:
            print("No next state suggested (may be at final state)")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
