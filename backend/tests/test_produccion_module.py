"""
Test suite for Production Module (Servicios, Personas, Movimientos de Producción)
Tests CRUD operations and business logic validations
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test data IDs from main agent context
SERVICIO_CORTE_ID = "18dcc520-0e9f-41e6-bdaf-928da9911884"
SERVICIO_COSTURA_ID = "7e21bd03-e1a3-40e9-9a77-e67876bfdf39"
PERSONA_JUAN_ID = "512643ec-1d00-4bab-a6b9-df630004b986"
REGISTRO_TEST_ID = "9e1087a9-73cb-4d1a-b70a-bd135301d07b"


class TestServiciosProduccion:
    """Tests for Servicios de Producción CRUD"""
    
    def test_get_servicios_produccion(self):
        """GET /api/servicios-produccion - List all services"""
        response = requests.get(f"{BASE_URL}/api/servicios-produccion")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Verify test data exists
        nombres = [s['nombre'] for s in data]
        assert 'Corte' in nombres
        assert 'Costura' in nombres
        print(f"✓ GET servicios-produccion: {len(data)} servicios found")
    
    def test_servicios_sorted_by_secuencia(self):
        """Verify services are sorted by secuencia"""
        response = requests.get(f"{BASE_URL}/api/servicios-produccion")
        assert response.status_code == 200
        data = response.json()
        if len(data) > 1:
            secuencias = [s.get('secuencia', 0) for s in data]
            assert secuencias == sorted(secuencias), "Services should be sorted by secuencia"
        print("✓ Services sorted by secuencia")
    
    def test_create_servicio_produccion(self):
        """POST /api/servicios-produccion - Create new service"""
        payload = {
            "nombre": f"TEST_Servicio_{uuid.uuid4().hex[:6]}",
            "secuencia": 99
        }
        response = requests.post(f"{BASE_URL}/api/servicios-produccion", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data['nombre'] == payload['nombre']
        assert data['secuencia'] == 99
        assert 'id' in data
        print(f"✓ POST servicios-produccion: Created {data['nombre']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/servicios-produccion/{data['id']}")
    
    def test_update_servicio_produccion(self):
        """PUT /api/servicios-produccion/{id} - Update service"""
        # Create test service
        create_payload = {"nombre": f"TEST_Update_{uuid.uuid4().hex[:6]}", "secuencia": 50}
        create_response = requests.post(f"{BASE_URL}/api/servicios-produccion", json=create_payload)
        assert create_response.status_code == 200
        servicio_id = create_response.json()['id']
        
        # Update
        update_payload = {"nombre": "TEST_Updated_Name", "secuencia": 51}
        update_response = requests.put(f"{BASE_URL}/api/servicios-produccion/{servicio_id}", json=update_payload)
        assert update_response.status_code == 200
        data = update_response.json()
        assert data['nombre'] == "TEST_Updated_Name"
        assert data['secuencia'] == 51
        print("✓ PUT servicios-produccion: Updated successfully")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/servicios-produccion/{servicio_id}")
    
    def test_delete_servicio_produccion(self):
        """DELETE /api/servicios-produccion/{id} - Delete service"""
        # Create test service
        create_payload = {"nombre": f"TEST_Delete_{uuid.uuid4().hex[:6]}", "secuencia": 100}
        create_response = requests.post(f"{BASE_URL}/api/servicios-produccion", json=create_payload)
        assert create_response.status_code == 200
        servicio_id = create_response.json()['id']
        
        # Delete
        delete_response = requests.delete(f"{BASE_URL}/api/servicios-produccion/{servicio_id}")
        assert delete_response.status_code == 200
        
        # Verify deleted
        get_response = requests.get(f"{BASE_URL}/api/servicios-produccion")
        ids = [s['id'] for s in get_response.json()]
        assert servicio_id not in ids
        print("✓ DELETE servicios-produccion: Deleted successfully")
    
    def test_delete_nonexistent_servicio(self):
        """DELETE /api/servicios-produccion/{id} - 404 for nonexistent"""
        response = requests.delete(f"{BASE_URL}/api/servicios-produccion/nonexistent-id")
        assert response.status_code == 404
        print("✓ DELETE nonexistent servicio returns 404")


class TestPersonasProduccion:
    """Tests for Personas de Producción CRUD"""
    
    def test_get_personas_produccion(self):
        """GET /api/personas-produccion - List all personas"""
        response = requests.get(f"{BASE_URL}/api/personas-produccion")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Verify test data exists
        nombres = [p['nombre'] for p in data]
        assert 'Juan Pérez' in nombres
        print(f"✓ GET personas-produccion: {len(data)} personas found")
    
    def test_get_personas_with_servicios_nombres(self):
        """Verify personas include servicios_nombres"""
        response = requests.get(f"{BASE_URL}/api/personas-produccion")
        assert response.status_code == 200
        data = response.json()
        juan = next((p for p in data if p['nombre'] == 'Juan Pérez'), None)
        assert juan is not None
        assert 'servicios_nombres' in juan
        assert 'Corte' in juan['servicios_nombres']
        assert 'Costura' in juan['servicios_nombres']
        print("✓ Personas include servicios_nombres")
    
    def test_filter_personas_by_servicio(self):
        """GET /api/personas-produccion?servicio_id=X - Filter by service"""
        response = requests.get(f"{BASE_URL}/api/personas-produccion?servicio_id={SERVICIO_CORTE_ID}")
        assert response.status_code == 200
        data = response.json()
        # All returned personas should have this servicio_id
        for persona in data:
            assert SERVICIO_CORTE_ID in persona.get('servicio_ids', [])
        print(f"✓ Filter personas by servicio_id: {len(data)} personas")
    
    def test_filter_personas_by_activo(self):
        """GET /api/personas-produccion?activo=true - Filter by active status"""
        response = requests.get(f"{BASE_URL}/api/personas-produccion?activo=true")
        assert response.status_code == 200
        data = response.json()
        for persona in data:
            assert persona.get('activo', True) == True
        print(f"✓ Filter personas by activo=true: {len(data)} personas")
    
    def test_create_persona_produccion(self):
        """POST /api/personas-produccion - Create new persona"""
        payload = {
            "nombre": f"TEST_Persona_{uuid.uuid4().hex[:6]}",
            "servicio_ids": [SERVICIO_CORTE_ID],
            "telefono": "123456789",
            "activo": True
        }
        response = requests.post(f"{BASE_URL}/api/personas-produccion", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data['nombre'] == payload['nombre']
        assert SERVICIO_CORTE_ID in data['servicio_ids']
        assert data['telefono'] == "123456789"
        assert data['activo'] == True
        assert 'id' in data
        print(f"✓ POST personas-produccion: Created {data['nombre']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/personas-produccion/{data['id']}")
    
    def test_create_persona_multiple_servicios(self):
        """POST /api/personas-produccion - Create with multiple services"""
        payload = {
            "nombre": f"TEST_MultiServ_{uuid.uuid4().hex[:6]}",
            "servicio_ids": [SERVICIO_CORTE_ID, SERVICIO_COSTURA_ID],
            "telefono": "",
            "activo": True
        }
        response = requests.post(f"{BASE_URL}/api/personas-produccion", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert len(data['servicio_ids']) == 2
        assert SERVICIO_CORTE_ID in data['servicio_ids']
        assert SERVICIO_COSTURA_ID in data['servicio_ids']
        print("✓ Created persona with multiple servicios")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/personas-produccion/{data['id']}")
    
    def test_update_persona_produccion(self):
        """PUT /api/personas-produccion/{id} - Update persona"""
        # Create test persona
        create_payload = {
            "nombre": f"TEST_Update_{uuid.uuid4().hex[:6]}",
            "servicio_ids": [SERVICIO_CORTE_ID],
            "telefono": "111",
            "activo": True
        }
        create_response = requests.post(f"{BASE_URL}/api/personas-produccion", json=create_payload)
        assert create_response.status_code == 200
        persona_id = create_response.json()['id']
        
        # Update
        update_payload = {
            "nombre": "TEST_Updated_Persona",
            "servicio_ids": [SERVICIO_COSTURA_ID],
            "telefono": "222",
            "activo": False
        }
        update_response = requests.put(f"{BASE_URL}/api/personas-produccion/{persona_id}", json=update_payload)
        assert update_response.status_code == 200
        data = update_response.json()
        assert data['nombre'] == "TEST_Updated_Persona"
        assert data['activo'] == False
        print("✓ PUT personas-produccion: Updated successfully")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/personas-produccion/{persona_id}")
    
    def test_toggle_persona_activo(self):
        """Toggle persona activo status"""
        # Create test persona
        create_payload = {
            "nombre": f"TEST_Toggle_{uuid.uuid4().hex[:6]}",
            "servicio_ids": [SERVICIO_CORTE_ID],
            "telefono": "",
            "activo": True
        }
        create_response = requests.post(f"{BASE_URL}/api/personas-produccion", json=create_payload)
        assert create_response.status_code == 200
        persona_id = create_response.json()['id']
        
        # Toggle to inactive
        update_payload = {**create_payload, "activo": False}
        update_response = requests.put(f"{BASE_URL}/api/personas-produccion/{persona_id}", json=update_payload)
        assert update_response.status_code == 200
        assert update_response.json()['activo'] == False
        print("✓ Toggle persona activo status works")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/personas-produccion/{persona_id}")
    
    def test_delete_persona_produccion(self):
        """DELETE /api/personas-produccion/{id} - Delete persona"""
        # Create test persona
        create_payload = {
            "nombre": f"TEST_Delete_{uuid.uuid4().hex[:6]}",
            "servicio_ids": [SERVICIO_CORTE_ID],
            "telefono": "",
            "activo": True
        }
        create_response = requests.post(f"{BASE_URL}/api/personas-produccion", json=create_payload)
        assert create_response.status_code == 200
        persona_id = create_response.json()['id']
        
        # Delete
        delete_response = requests.delete(f"{BASE_URL}/api/personas-produccion/{persona_id}")
        assert delete_response.status_code == 200
        print("✓ DELETE personas-produccion: Deleted successfully")


class TestMovimientosProduccion:
    """Tests for Movimientos de Producción CRUD"""
    
    def test_get_movimientos_produccion(self):
        """GET /api/movimientos-produccion - List all movimientos"""
        response = requests.get(f"{BASE_URL}/api/movimientos-produccion")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET movimientos-produccion: {len(data)} movimientos found")
    
    def test_get_movimientos_with_details(self):
        """Verify movimientos include servicio_nombre, persona_nombre, registro_n_corte"""
        response = requests.get(f"{BASE_URL}/api/movimientos-produccion")
        assert response.status_code == 200
        data = response.json()
        if len(data) > 0:
            mov = data[0]
            assert 'servicio_nombre' in mov
            assert 'persona_nombre' in mov
            assert 'registro_n_corte' in mov
        print("✓ Movimientos include related names")
    
    def test_filter_movimientos_by_registro(self):
        """GET /api/movimientos-produccion?registro_id=X - Filter by registro"""
        response = requests.get(f"{BASE_URL}/api/movimientos-produccion?registro_id={REGISTRO_TEST_ID}")
        assert response.status_code == 200
        data = response.json()
        for mov in data:
            assert mov['registro_id'] == REGISTRO_TEST_ID
        print(f"✓ Filter movimientos by registro_id: {len(data)} movimientos")
    
    def test_create_movimiento_produccion(self):
        """POST /api/movimientos-produccion - Create new movimiento"""
        payload = {
            "registro_id": REGISTRO_TEST_ID,
            "servicio_id": SERVICIO_CORTE_ID,
            "persona_id": PERSONA_JUAN_ID,
            "fecha_inicio": "2025-01-20",
            "fecha_fin": "2025-01-21",
            "cantidad": 50,
            "observaciones": "TEST movimiento"
        }
        response = requests.post(f"{BASE_URL}/api/movimientos-produccion", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data['registro_id'] == REGISTRO_TEST_ID
        assert data['servicio_id'] == SERVICIO_CORTE_ID
        assert data['persona_id'] == PERSONA_JUAN_ID
        assert data['cantidad'] == 50
        assert 'id' in data
        print(f"✓ POST movimientos-produccion: Created movimiento")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/movimientos-produccion/{data['id']}")
    
    def test_create_movimiento_invalid_registro(self):
        """POST /api/movimientos-produccion - 404 for invalid registro"""
        payload = {
            "registro_id": "nonexistent-registro-id",
            "servicio_id": SERVICIO_CORTE_ID,
            "persona_id": PERSONA_JUAN_ID,
            "cantidad": 10
        }
        response = requests.post(f"{BASE_URL}/api/movimientos-produccion", json=payload)
        assert response.status_code == 404
        assert "Registro no encontrado" in response.json().get('detail', '')
        print("✓ Invalid registro returns 404")
    
    def test_create_movimiento_invalid_servicio(self):
        """POST /api/movimientos-produccion - 404 for invalid servicio"""
        payload = {
            "registro_id": REGISTRO_TEST_ID,
            "servicio_id": "nonexistent-servicio-id",
            "persona_id": PERSONA_JUAN_ID,
            "cantidad": 10
        }
        response = requests.post(f"{BASE_URL}/api/movimientos-produccion", json=payload)
        assert response.status_code == 404
        assert "Servicio no encontrado" in response.json().get('detail', '')
        print("✓ Invalid servicio returns 404")
    
    def test_create_movimiento_invalid_persona(self):
        """POST /api/movimientos-produccion - 404 for invalid persona"""
        payload = {
            "registro_id": REGISTRO_TEST_ID,
            "servicio_id": SERVICIO_CORTE_ID,
            "persona_id": "nonexistent-persona-id",
            "cantidad": 10
        }
        response = requests.post(f"{BASE_URL}/api/movimientos-produccion", json=payload)
        assert response.status_code == 404
        assert "Persona no encontrada" in response.json().get('detail', '')
        print("✓ Invalid persona returns 404")
    
    def test_create_movimiento_persona_without_servicio(self):
        """POST /api/movimientos-produccion - 400 if persona doesn't have servicio"""
        # Create a persona without SERVICIO_COSTURA_ID
        persona_payload = {
            "nombre": f"TEST_NoServ_{uuid.uuid4().hex[:6]}",
            "servicio_ids": [SERVICIO_CORTE_ID],  # Only Corte, not Costura
            "telefono": "",
            "activo": True
        }
        persona_response = requests.post(f"{BASE_URL}/api/personas-produccion", json=persona_payload)
        assert persona_response.status_code == 200
        persona_id = persona_response.json()['id']
        
        # Try to create movimiento with Costura service
        mov_payload = {
            "registro_id": REGISTRO_TEST_ID,
            "servicio_id": SERVICIO_COSTURA_ID,  # Costura
            "persona_id": persona_id,  # Persona only has Corte
            "cantidad": 10
        }
        mov_response = requests.post(f"{BASE_URL}/api/movimientos-produccion", json=mov_payload)
        assert mov_response.status_code == 400
        assert "no tiene asignado este servicio" in mov_response.json().get('detail', '')
        print("✓ Persona without servicio returns 400")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/personas-produccion/{persona_id}")
    
    def test_update_movimiento_produccion(self):
        """PUT /api/movimientos-produccion/{id} - Update movimiento"""
        # Create test movimiento
        create_payload = {
            "registro_id": REGISTRO_TEST_ID,
            "servicio_id": SERVICIO_CORTE_ID,
            "persona_id": PERSONA_JUAN_ID,
            "cantidad": 25,
            "observaciones": "Original"
        }
        create_response = requests.post(f"{BASE_URL}/api/movimientos-produccion", json=create_payload)
        assert create_response.status_code == 200
        mov_id = create_response.json()['id']
        
        # Update
        update_payload = {
            "registro_id": REGISTRO_TEST_ID,
            "servicio_id": SERVICIO_CORTE_ID,
            "persona_id": PERSONA_JUAN_ID,
            "cantidad": 75,
            "observaciones": "Updated"
        }
        update_response = requests.put(f"{BASE_URL}/api/movimientos-produccion/{mov_id}", json=update_payload)
        assert update_response.status_code == 200
        data = update_response.json()
        assert data['cantidad'] == 75
        assert data['observaciones'] == "Updated"
        print("✓ PUT movimientos-produccion: Updated successfully")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/movimientos-produccion/{mov_id}")
    
    def test_delete_movimiento_produccion(self):
        """DELETE /api/movimientos-produccion/{id} - Delete movimiento"""
        # Create test movimiento
        create_payload = {
            "registro_id": REGISTRO_TEST_ID,
            "servicio_id": SERVICIO_CORTE_ID,
            "persona_id": PERSONA_JUAN_ID,
            "cantidad": 10
        }
        create_response = requests.post(f"{BASE_URL}/api/movimientos-produccion", json=create_payload)
        assert create_response.status_code == 200
        mov_id = create_response.json()['id']
        
        # Delete
        delete_response = requests.delete(f"{BASE_URL}/api/movimientos-produccion/{mov_id}")
        assert delete_response.status_code == 200
        print("✓ DELETE movimientos-produccion: Deleted successfully")
    
    def test_delete_nonexistent_movimiento(self):
        """DELETE /api/movimientos-produccion/{id} - 404 for nonexistent"""
        response = requests.delete(f"{BASE_URL}/api/movimientos-produccion/nonexistent-id")
        assert response.status_code == 404
        print("✓ DELETE nonexistent movimiento returns 404")


class TestIntegration:
    """Integration tests for the production module"""
    
    def test_full_workflow(self):
        """Test complete workflow: Create servicio -> Create persona -> Create movimiento"""
        # 1. Create servicio
        servicio_payload = {"nombre": f"TEST_Workflow_{uuid.uuid4().hex[:6]}", "secuencia": 999}
        servicio_response = requests.post(f"{BASE_URL}/api/servicios-produccion", json=servicio_payload)
        assert servicio_response.status_code == 200
        servicio_id = servicio_response.json()['id']
        
        # 2. Create persona with this servicio
        persona_payload = {
            "nombre": f"TEST_Worker_{uuid.uuid4().hex[:6]}",
            "servicio_ids": [servicio_id],
            "telefono": "555-1234",
            "activo": True
        }
        persona_response = requests.post(f"{BASE_URL}/api/personas-produccion", json=persona_payload)
        assert persona_response.status_code == 200
        persona_id = persona_response.json()['id']
        
        # 3. Create movimiento with this persona and servicio
        mov_payload = {
            "registro_id": REGISTRO_TEST_ID,
            "servicio_id": servicio_id,
            "persona_id": persona_id,
            "fecha_inicio": "2025-01-22",
            "cantidad": 100,
            "observaciones": "Workflow test"
        }
        mov_response = requests.post(f"{BASE_URL}/api/movimientos-produccion", json=mov_payload)
        assert mov_response.status_code == 200
        mov_id = mov_response.json()['id']
        
        # 4. Verify movimiento has correct details
        get_response = requests.get(f"{BASE_URL}/api/movimientos-produccion?registro_id={REGISTRO_TEST_ID}")
        assert get_response.status_code == 200
        movimientos = get_response.json()
        test_mov = next((m for m in movimientos if m['id'] == mov_id), None)
        assert test_mov is not None
        assert test_mov['servicio_nombre'] == servicio_payload['nombre']
        assert test_mov['persona_nombre'] == persona_payload['nombre']
        
        print("✓ Full workflow test passed")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/movimientos-produccion/{mov_id}")
        requests.delete(f"{BASE_URL}/api/personas-produccion/{persona_id}")
        requests.delete(f"{BASE_URL}/api/servicios-produccion/{servicio_id}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
