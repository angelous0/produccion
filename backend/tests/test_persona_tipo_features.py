"""
Test: Persona Tipo (INTERNO/EXTERNO) features in personas-produccion and movimientos-produccion APIs.

Features tested:
1. GET /api/personas-produccion returns tipo_persona and unidad_interna_nombre
2. GET /api/movimientos-produccion returns persona_tipo and unidad_interna_nombre
3. PUT /api/personas-produccion updates tipo_persona and unidad_interna_id
4. GET /api/unidades-internas returns list of internal units
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username": "eduard",
        "password": "eduard123"
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Authentication failed - skipping tests")

@pytest.fixture
def auth_headers(auth_token):
    """Return headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


class TestPersonasProduccionTipo:
    """Test persona tipo (INTERNO/EXTERNO) in personas-produccion"""
    
    def test_get_personas_returns_tipo_persona(self, auth_headers):
        """GET /api/personas-produccion returns tipo_persona field"""
        response = requests.get(f"{BASE_URL}/api/personas-produccion", headers=auth_headers)
        assert response.status_code == 200
        
        personas = response.json()
        assert isinstance(personas, list)
        assert len(personas) > 0, "No personas found - need seed data"
        
        # Check each persona has tipo_persona field
        for persona in personas:
            assert 'tipo_persona' in persona, f"Persona {persona.get('nombre')} missing tipo_persona"
            assert persona['tipo_persona'] in ['INTERNO', 'EXTERNO'], f"Invalid tipo_persona: {persona['tipo_persona']}"
            print(f"Persona: {persona['nombre']} - tipo: {persona['tipo_persona']}")
            
            # If INTERNO, check for unidad_interna_nombre
            if persona['tipo_persona'] == 'INTERNO' and persona.get('unidad_interna_id'):
                assert 'unidad_interna_nombre' in persona, f"INTERNO persona missing unidad_interna_nombre"
                print(f"  -> Unidad interna: {persona.get('unidad_interna_nombre')}")

    def test_find_interno_persona(self, auth_headers):
        """Find a persona with tipo_persona='INTERNO' and verify unidad_interna_nombre"""
        response = requests.get(f"{BASE_URL}/api/personas-produccion", headers=auth_headers)
        assert response.status_code == 200
        
        personas = response.json()
        interno_personas = [p for p in personas if p.get('tipo_persona') == 'INTERNO']
        
        print(f"Found {len(interno_personas)} INTERNO personas")
        
        # Look for "Interno" persona mentioned in test context
        interno_with_unidad = [p for p in interno_personas if p.get('unidad_interna_nombre')]
        if interno_with_unidad:
            p = interno_with_unidad[0]
            print(f"INTERNO with unidad: {p['nombre']} -> {p['unidad_interna_nombre']}")
            assert p['unidad_interna_nombre'], "unidad_interna_nombre should not be empty"

    def test_find_externo_persona(self, auth_headers):
        """Find a persona with tipo_persona='EXTERNO'"""
        response = requests.get(f"{BASE_URL}/api/personas-produccion", headers=auth_headers)
        assert response.status_code == 200
        
        personas = response.json()
        externo_personas = [p for p in personas if p.get('tipo_persona') == 'EXTERNO']
        
        print(f"Found {len(externo_personas)} EXTERNO personas")
        assert len(externo_personas) > 0, "No EXTERNO personas found"
        
        p = externo_personas[0]
        print(f"EXTERNO persona: {p['nombre']}")
        # EXTERNO personas should NOT have unidad_interna_nombre
        assert p.get('unidad_interna_nombre') is None or p.get('unidad_interna_id') is None, \
            "EXTERNO persona should not have unidad_interna"


class TestMovimientosProduccionPersonaTipo:
    """Test persona_tipo and unidad_interna_nombre in movimientos-produccion"""

    def test_get_movimientos_returns_persona_tipo(self, auth_headers):
        """GET /api/movimientos-produccion returns persona_tipo field"""
        response = requests.get(f"{BASE_URL}/api/movimientos-produccion", headers=auth_headers)
        assert response.status_code == 200
        
        movimientos = response.json()
        assert isinstance(movimientos, list)
        
        if len(movimientos) == 0:
            pytest.skip("No movimientos found - need seed data")
        
        print(f"Found {len(movimientos)} movimientos")
        
        # Check movimientos have persona_tipo
        for mov in movimientos[:5]:  # Check first 5
            assert 'persona_tipo' in mov, f"Movimiento {mov.get('id')} missing persona_tipo"
            assert 'persona_nombre' in mov, f"Movimiento {mov.get('id')} missing persona_nombre"
            print(f"Mov: {mov.get('servicio_nombre')} - Persona: {mov.get('persona_nombre')} ({mov.get('persona_tipo')})")
            
            if mov.get('persona_tipo') == 'INTERNO' and mov.get('unidad_interna_nombre'):
                print(f"  -> Unidad interna: {mov.get('unidad_interna_nombre')}")

    def test_get_movimientos_by_registro(self, auth_headers):
        """GET /api/movimientos-produccion?registro_id=... returns persona_tipo"""
        # Use registro 01 which should have INTERNO persona per test context
        # registro_id = c74d3460-3e8b-4d4c-88e5-06bff012d6f5
        registro_id = "c74d3460-3e8b-4d4c-88e5-06bff012d6f5"
        
        response = requests.get(
            f"{BASE_URL}/api/movimientos-produccion?registro_id={registro_id}", 
            headers=auth_headers
        )
        assert response.status_code == 200
        
        movimientos = response.json()
        print(f"Found {len(movimientos)} movimientos for registro {registro_id}")
        
        if len(movimientos) > 0:
            for mov in movimientos:
                persona_tipo = mov.get('persona_tipo')
                persona_nombre = mov.get('persona_nombre')
                unidad = mov.get('unidad_interna_nombre')
                print(f"  -> {persona_nombre} ({persona_tipo}) - Unidad: {unidad or 'N/A'}")
                
                # Verify estructura
                assert 'persona_tipo' in mov
                assert persona_tipo in ['INTERNO', 'EXTERNO', None]


class TestUnidadesInternas:
    """Test unidades-internas endpoint"""
    
    def test_get_unidades_internas(self, auth_headers):
        """GET /api/unidades-internas returns list of internal units"""
        response = requests.get(f"{BASE_URL}/api/unidades-internas", headers=auth_headers)
        assert response.status_code == 200
        
        unidades = response.json()
        assert isinstance(unidades, list)
        print(f"Found {len(unidades)} unidades internas")
        
        if len(unidades) > 0:
            for u in unidades[:5]:  # Show first 5
                assert 'id' in u
                assert 'nombre' in u
                print(f"  -> {u['nombre']} (id: {u['id']})")


class TestPersonasProduccionUpdate:
    """Test updating persona tipo_persona and unidad_interna"""
    
    def test_create_and_update_persona_tipo(self, auth_headers):
        """Create a persona and update tipo_persona"""
        import uuid
        
        # First get a service id to assign
        services_resp = requests.get(f"{BASE_URL}/api/servicios-produccion", headers=auth_headers)
        services = services_resp.json()
        if not services:
            pytest.skip("No services found")
        service_id = services[0]['id']
        
        # Get unidades internas for INTERNO persona
        unidades_resp = requests.get(f"{BASE_URL}/api/unidades-internas", headers=auth_headers)
        unidades = unidades_resp.json()
        unidad_id = unidades[0]['id'] if unidades else None
        
        test_name = f"TEST_Persona_{uuid.uuid4().hex[:8]}"
        
        # Create persona as EXTERNO
        create_data = {
            "nombre": test_name,
            "servicios": [{"servicio_id": service_id, "tarifa": 1.5}],
            "telefono": "999888777",
            "direccion": "Test Address",
            "activo": True,
            "tipo_persona": "EXTERNO",
            "unidad_interna_id": None
        }
        
        create_resp = requests.post(
            f"{BASE_URL}/api/personas-produccion",
            json=create_data,
            headers=auth_headers
        )
        assert create_resp.status_code == 200, f"Create failed: {create_resp.text}"
        created = create_resp.json()
        persona_id = created['id']
        print(f"Created persona: {test_name} (EXTERNO)")
        
        try:
            # Update to INTERNO with unidad_interna
            update_data = {
                "nombre": test_name,
                "servicios": [{"servicio_id": service_id, "tarifa": 2.0}],
                "telefono": "999888777",
                "direccion": "Test Address",
                "activo": True,
                "tipo_persona": "INTERNO",
                "unidad_interna_id": unidad_id
            }
            
            update_resp = requests.put(
                f"{BASE_URL}/api/personas-produccion/{persona_id}",
                json=update_data,
                headers=auth_headers
            )
            assert update_resp.status_code == 200, f"Update failed: {update_resp.text}"
            print(f"Updated persona to INTERNO with unidad_id: {unidad_id}")
            
            # Verify by fetching
            get_resp = requests.get(f"{BASE_URL}/api/personas-produccion", headers=auth_headers)
            personas = get_resp.json()
            updated_persona = next((p for p in personas if p['id'] == persona_id), None)
            
            assert updated_persona is not None, "Couldn't find updated persona"
            assert updated_persona['tipo_persona'] == 'INTERNO', f"Expected INTERNO, got {updated_persona['tipo_persona']}"
            
            if unidad_id:
                assert updated_persona.get('unidad_interna_id') == unidad_id
                assert updated_persona.get('unidad_interna_nombre') is not None
                print(f"Verified: tipo_persona=INTERNO, unidad_interna_nombre={updated_persona.get('unidad_interna_nombre')}")
            
        finally:
            # Cleanup - delete test persona
            delete_resp = requests.delete(
                f"{BASE_URL}/api/personas-produccion/{persona_id}",
                headers=auth_headers
            )
            print(f"Cleanup: deleted test persona {persona_id}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
