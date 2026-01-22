"""
Test suite for Rutas de Producción and BOM (Bill of Materials) features
Tests CRUD operations for production routes and model configuration with materials/services
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Existing test data IDs
SERVICIO_CORTE_ID = "18dcc520-0e9f-41e6-bdaf-928da9911884"
SERVICIO_COSTURA_ID = "a5a2705e-3e93-4e98-bb9a-8a25d04ec37e"
RUTA_ESTANDAR_ID = "5b27fb94-a704-43a9-a4c6-e3d05e5e280b"
MODELO_EDUARD_ID = "5180c7f2-13cc-4f81-8cd6-53c96e68f55c"


class TestRutasProduccion:
    """Tests for Rutas de Producción CRUD"""
    
    def test_get_rutas_produccion(self):
        """GET /api/rutas-produccion - List all production routes"""
        response = requests.get(f"{BASE_URL}/api/rutas-produccion")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET rutas-produccion: {len(data)} rutas found")
    
    def test_ruta_estandar_exists(self):
        """Verify 'Ruta Estándar' exists with correct structure"""
        response = requests.get(f"{BASE_URL}/api/rutas-produccion")
        assert response.status_code == 200
        data = response.json()
        ruta_estandar = next((r for r in data if r['nombre'] == 'Ruta Estándar'), None)
        assert ruta_estandar is not None, "Ruta Estándar should exist"
        assert 'etapas' in ruta_estandar
        assert len(ruta_estandar['etapas']) >= 2, "Should have at least 2 etapas"
        print(f"✓ Ruta Estándar exists with {len(ruta_estandar['etapas'])} etapas")
    
    def test_ruta_etapas_have_servicio_nombre(self):
        """Verify etapas include servicio_nombre"""
        response = requests.get(f"{BASE_URL}/api/rutas-produccion")
        assert response.status_code == 200
        data = response.json()
        if len(data) > 0:
            ruta = data[0]
            for etapa in ruta.get('etapas', []):
                assert 'servicio_nombre' in etapa, "Etapa should have servicio_nombre"
        print("✓ Etapas include servicio_nombre")
    
    def test_get_ruta_by_id(self):
        """GET /api/rutas-produccion/{id} - Get single route"""
        response = requests.get(f"{BASE_URL}/api/rutas-produccion/{RUTA_ESTANDAR_ID}")
        assert response.status_code == 200
        data = response.json()
        assert data['id'] == RUTA_ESTANDAR_ID
        assert data['nombre'] == 'Ruta Estándar'
        assert 'etapas' in data
        print("✓ GET ruta by ID works")
    
    def test_get_nonexistent_ruta(self):
        """GET /api/rutas-produccion/{id} - 404 for nonexistent"""
        response = requests.get(f"{BASE_URL}/api/rutas-produccion/nonexistent-id")
        assert response.status_code == 404
        print("✓ GET nonexistent ruta returns 404")
    
    def test_create_ruta_produccion(self):
        """POST /api/rutas-produccion - Create new route"""
        payload = {
            "nombre": f"TEST_Ruta_{uuid.uuid4().hex[:6]}",
            "descripcion": "Test route description",
            "etapas": [
                {"servicio_id": SERVICIO_CORTE_ID, "orden": 0},
                {"servicio_id": SERVICIO_COSTURA_ID, "orden": 1}
            ]
        }
        response = requests.post(f"{BASE_URL}/api/rutas-produccion", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data['nombre'] == payload['nombre']
        assert data['descripcion'] == payload['descripcion']
        assert len(data['etapas']) == 2
        assert 'id' in data
        print(f"✓ POST rutas-produccion: Created {data['nombre']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/rutas-produccion/{data['id']}")
    
    def test_create_ruta_empty_etapas(self):
        """POST /api/rutas-produccion - Create route with empty etapas"""
        payload = {
            "nombre": f"TEST_EmptyEtapas_{uuid.uuid4().hex[:6]}",
            "descripcion": "",
            "etapas": []
        }
        response = requests.post(f"{BASE_URL}/api/rutas-produccion", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert len(data['etapas']) == 0
        print("✓ Created ruta with empty etapas")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/rutas-produccion/{data['id']}")
    
    def test_update_ruta_produccion(self):
        """PUT /api/rutas-produccion/{id} - Update route"""
        # Create test route
        create_payload = {
            "nombre": f"TEST_Update_{uuid.uuid4().hex[:6]}",
            "descripcion": "Original",
            "etapas": [{"servicio_id": SERVICIO_CORTE_ID, "orden": 0}]
        }
        create_response = requests.post(f"{BASE_URL}/api/rutas-produccion", json=create_payload)
        assert create_response.status_code == 200
        ruta_id = create_response.json()['id']
        
        # Update
        update_payload = {
            "nombre": "TEST_Updated_Ruta",
            "descripcion": "Updated description",
            "etapas": [
                {"servicio_id": SERVICIO_CORTE_ID, "orden": 0},
                {"servicio_id": SERVICIO_COSTURA_ID, "orden": 1}
            ]
        }
        update_response = requests.put(f"{BASE_URL}/api/rutas-produccion/{ruta_id}", json=update_payload)
        assert update_response.status_code == 200
        data = update_response.json()
        assert data['nombre'] == "TEST_Updated_Ruta"
        assert data['descripcion'] == "Updated description"
        assert len(data['etapas']) == 2
        print("✓ PUT rutas-produccion: Updated successfully")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/rutas-produccion/{ruta_id}")
    
    def test_delete_ruta_produccion(self):
        """DELETE /api/rutas-produccion/{id} - Delete route"""
        # Create test route
        create_payload = {
            "nombre": f"TEST_Delete_{uuid.uuid4().hex[:6]}",
            "descripcion": "",
            "etapas": []
        }
        create_response = requests.post(f"{BASE_URL}/api/rutas-produccion", json=create_payload)
        assert create_response.status_code == 200
        ruta_id = create_response.json()['id']
        
        # Delete
        delete_response = requests.delete(f"{BASE_URL}/api/rutas-produccion/{ruta_id}")
        assert delete_response.status_code == 200
        
        # Verify deleted
        get_response = requests.get(f"{BASE_URL}/api/rutas-produccion/{ruta_id}")
        assert get_response.status_code == 404
        print("✓ DELETE rutas-produccion: Deleted successfully")
    
    def test_delete_ruta_with_modelos_blocked(self):
        """DELETE /api/rutas-produccion/{id} - Should be blocked if models use it"""
        # Ruta Estándar is used by modelo Eduard
        response = requests.delete(f"{BASE_URL}/api/rutas-produccion/{RUTA_ESTANDAR_ID}")
        assert response.status_code == 400
        assert "modelo" in response.json().get('detail', '').lower()
        print("✓ DELETE ruta with modelos is blocked")
    
    def test_delete_nonexistent_ruta(self):
        """DELETE /api/rutas-produccion/{id} - 404 for nonexistent"""
        response = requests.delete(f"{BASE_URL}/api/rutas-produccion/nonexistent-id")
        assert response.status_code == 404
        print("✓ DELETE nonexistent ruta returns 404")


class TestModelosWithRutaAndBOM:
    """Tests for Modelos with production routes and BOM"""
    
    def test_get_modelos(self):
        """GET /api/modelos - List all models"""
        response = requests.get(f"{BASE_URL}/api/modelos")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET modelos: {len(data)} modelos found")
    
    def test_modelo_eduard_has_ruta(self):
        """Verify modelo Eduard has ruta_produccion_id assigned"""
        response = requests.get(f"{BASE_URL}/api/modelos")
        assert response.status_code == 200
        data = response.json()
        eduard = next((m for m in data if m['nombre'] == 'Eduard'), None)
        assert eduard is not None, "Modelo Eduard should exist"
        assert eduard.get('ruta_produccion_id') == RUTA_ESTANDAR_ID
        assert eduard.get('ruta_nombre') == 'Ruta Estándar'
        print("✓ Modelo Eduard has Ruta Estándar assigned")
    
    def test_modelo_includes_ruta_nombre(self):
        """Verify modelos include ruta_nombre in response"""
        response = requests.get(f"{BASE_URL}/api/modelos")
        assert response.status_code == 200
        data = response.json()
        for modelo in data:
            if modelo.get('ruta_produccion_id'):
                assert 'ruta_nombre' in modelo
        print("✓ Modelos include ruta_nombre")
    
    def test_get_modelo_detalle(self):
        """GET /api/modelos/{id} - Get model detail with enriched data"""
        response = requests.get(f"{BASE_URL}/api/modelos/{MODELO_EDUARD_ID}")
        assert response.status_code == 200
        data = response.json()
        assert data['id'] == MODELO_EDUARD_ID
        assert data['nombre'] == 'Eduard'
        # Check enriched fields
        assert 'marca_nombre' in data
        assert 'tipo_nombre' in data
        assert 'ruta_nombre' in data
        assert 'materiales_detalle' in data
        assert 'servicios_detalle' in data
        print("✓ GET modelo detalle includes enriched data")
    
    def test_modelo_detalle_includes_ruta_etapas(self):
        """Verify modelo detail includes ruta_etapas when has ruta"""
        response = requests.get(f"{BASE_URL}/api/modelos/{MODELO_EDUARD_ID}")
        assert response.status_code == 200
        data = response.json()
        if data.get('ruta_produccion_id'):
            assert 'ruta_etapas' in data
            assert isinstance(data['ruta_etapas'], list)
            for etapa in data['ruta_etapas']:
                assert 'servicio_id' in etapa
                assert 'servicio_nombre' in etapa
                assert 'orden' in etapa
        print("✓ Modelo detalle includes ruta_etapas")
    
    def test_create_modelo_with_ruta(self):
        """POST /api/modelos - Create model with production route"""
        # First get required IDs
        marcas = requests.get(f"{BASE_URL}/api/marcas").json()
        tipos = requests.get(f"{BASE_URL}/api/tipos").json()
        entalles = requests.get(f"{BASE_URL}/api/entalles").json()
        telas = requests.get(f"{BASE_URL}/api/telas").json()
        hilos = requests.get(f"{BASE_URL}/api/hilos").json()
        
        payload = {
            "nombre": f"TEST_Modelo_{uuid.uuid4().hex[:6]}",
            "marca_id": marcas[0]['id'] if marcas else "",
            "tipo_id": tipos[0]['id'] if tipos else "",
            "entalle_id": entalles[0]['id'] if entalles else "",
            "tela_id": telas[0]['id'] if telas else "",
            "hilo_id": hilos[0]['id'] if hilos else "",
            "ruta_produccion_id": RUTA_ESTANDAR_ID,
            "materiales": [],
            "servicios_ids": []
        }
        response = requests.post(f"{BASE_URL}/api/modelos", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data['nombre'] == payload['nombre']
        assert data['ruta_produccion_id'] == RUTA_ESTANDAR_ID
        print(f"✓ POST modelos: Created {data['nombre']} with ruta")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/modelos/{data['id']}")
    
    def test_create_modelo_with_materiales(self):
        """POST /api/modelos - Create model with BOM (materiales)"""
        # Get required data
        marcas = requests.get(f"{BASE_URL}/api/marcas").json()
        tipos = requests.get(f"{BASE_URL}/api/tipos").json()
        entalles = requests.get(f"{BASE_URL}/api/entalles").json()
        telas = requests.get(f"{BASE_URL}/api/telas").json()
        hilos = requests.get(f"{BASE_URL}/api/hilos").json()
        inventario = requests.get(f"{BASE_URL}/api/inventario").json()
        
        materiales = []
        if inventario:
            materiales = [
                {"item_id": inventario[0]['id'], "cantidad_estimada": 2.5}
            ]
        
        payload = {
            "nombre": f"TEST_BOM_{uuid.uuid4().hex[:6]}",
            "marca_id": marcas[0]['id'] if marcas else "",
            "tipo_id": tipos[0]['id'] if tipos else "",
            "entalle_id": entalles[0]['id'] if entalles else "",
            "tela_id": telas[0]['id'] if telas else "",
            "hilo_id": hilos[0]['id'] if hilos else "",
            "ruta_produccion_id": None,
            "materiales": materiales,
            "servicios_ids": []
        }
        response = requests.post(f"{BASE_URL}/api/modelos", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data['nombre'] == payload['nombre']
        if materiales:
            assert len(data['materiales']) == 1
            assert data['materiales'][0]['cantidad_estimada'] == 2.5
        print(f"✓ POST modelos: Created {data['nombre']} with BOM")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/modelos/{data['id']}")
    
    def test_create_modelo_with_servicios(self):
        """POST /api/modelos - Create model with required services"""
        marcas = requests.get(f"{BASE_URL}/api/marcas").json()
        tipos = requests.get(f"{BASE_URL}/api/tipos").json()
        entalles = requests.get(f"{BASE_URL}/api/entalles").json()
        telas = requests.get(f"{BASE_URL}/api/telas").json()
        hilos = requests.get(f"{BASE_URL}/api/hilos").json()
        
        payload = {
            "nombre": f"TEST_Servicios_{uuid.uuid4().hex[:6]}",
            "marca_id": marcas[0]['id'] if marcas else "",
            "tipo_id": tipos[0]['id'] if tipos else "",
            "entalle_id": entalles[0]['id'] if entalles else "",
            "tela_id": telas[0]['id'] if telas else "",
            "hilo_id": hilos[0]['id'] if hilos else "",
            "ruta_produccion_id": None,
            "materiales": [],
            "servicios_ids": [SERVICIO_CORTE_ID, SERVICIO_COSTURA_ID]
        }
        response = requests.post(f"{BASE_URL}/api/modelos", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert len(data['servicios_ids']) == 2
        assert SERVICIO_CORTE_ID in data['servicios_ids']
        assert SERVICIO_COSTURA_ID in data['servicios_ids']
        print(f"✓ POST modelos: Created {data['nombre']} with servicios")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/modelos/{data['id']}")
    
    def test_update_modelo_ruta(self):
        """PUT /api/modelos/{id} - Update model's production route"""
        # Create test model without ruta
        marcas = requests.get(f"{BASE_URL}/api/marcas").json()
        tipos = requests.get(f"{BASE_URL}/api/tipos").json()
        entalles = requests.get(f"{BASE_URL}/api/entalles").json()
        telas = requests.get(f"{BASE_URL}/api/telas").json()
        hilos = requests.get(f"{BASE_URL}/api/hilos").json()
        
        create_payload = {
            "nombre": f"TEST_UpdateRuta_{uuid.uuid4().hex[:6]}",
            "marca_id": marcas[0]['id'] if marcas else "",
            "tipo_id": tipos[0]['id'] if tipos else "",
            "entalle_id": entalles[0]['id'] if entalles else "",
            "tela_id": telas[0]['id'] if telas else "",
            "hilo_id": hilos[0]['id'] if hilos else "",
            "ruta_produccion_id": None,
            "materiales": [],
            "servicios_ids": []
        }
        create_response = requests.post(f"{BASE_URL}/api/modelos", json=create_payload)
        assert create_response.status_code == 200
        modelo_id = create_response.json()['id']
        
        # Update with ruta
        update_payload = {**create_payload, "ruta_produccion_id": RUTA_ESTANDAR_ID}
        update_response = requests.put(f"{BASE_URL}/api/modelos/{modelo_id}", json=update_payload)
        assert update_response.status_code == 200
        data = update_response.json()
        assert data['ruta_produccion_id'] == RUTA_ESTANDAR_ID
        print("✓ PUT modelos: Updated ruta successfully")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/modelos/{modelo_id}")


class TestRegistroEstadosDisponibles:
    """Tests for dynamic estados based on production route"""
    
    def test_get_estados_globales(self):
        """GET /api/estados - Get global production states"""
        response = requests.get(f"{BASE_URL}/api/estados")
        assert response.status_code == 200
        data = response.json()
        assert 'estados' in data
        assert isinstance(data['estados'], list)
        assert len(data['estados']) > 0
        assert 'Para Corte' in data['estados']
        print(f"✓ GET estados: {len(data['estados'])} estados globales")
    
    def test_get_estados_disponibles_registro_with_ruta(self):
        """GET /api/registros/{id}/estados-disponibles - For registro with ruta"""
        # First get a registro that has a modelo with ruta
        registros = requests.get(f"{BASE_URL}/api/registros").json()
        registro_con_ruta = None
        for reg in registros:
            modelo = requests.get(f"{BASE_URL}/api/modelos/{reg['modelo_id']}").json()
            if modelo.get('ruta_produccion_id'):
                registro_con_ruta = reg
                break
        
        if registro_con_ruta:
            response = requests.get(f"{BASE_URL}/api/registros/{registro_con_ruta['id']}/estados-disponibles")
            assert response.status_code == 200
            data = response.json()
            assert 'estados' in data
            assert 'usa_ruta' in data
            assert 'estado_actual' in data
            if data['usa_ruta']:
                assert 'ruta_nombre' in data
                assert 'siguiente_estado' in data or data.get('estado_actual_idx') == len(data['estados']) - 1
            print(f"✓ GET estados-disponibles for registro with ruta: usa_ruta={data['usa_ruta']}")
        else:
            print("⚠ No registro with ruta found to test")
    
    def test_get_estados_disponibles_nonexistent_registro(self):
        """GET /api/registros/{id}/estados-disponibles - 404 for nonexistent"""
        response = requests.get(f"{BASE_URL}/api/registros/nonexistent-id/estados-disponibles")
        assert response.status_code == 404
        print("✓ GET estados-disponibles nonexistent returns 404")


class TestIntegrationRutasModelos:
    """Integration tests for rutas and modelos workflow"""
    
    def test_full_workflow_ruta_modelo_registro(self):
        """Test complete workflow: Create ruta -> Assign to modelo -> Check registro estados"""
        # 1. Create a new ruta
        ruta_payload = {
            "nombre": f"TEST_Workflow_{uuid.uuid4().hex[:6]}",
            "descripcion": "Workflow test route",
            "etapas": [
                {"servicio_id": SERVICIO_CORTE_ID, "orden": 0},
                {"servicio_id": SERVICIO_COSTURA_ID, "orden": 1}
            ]
        }
        ruta_response = requests.post(f"{BASE_URL}/api/rutas-produccion", json=ruta_payload)
        assert ruta_response.status_code == 200
        ruta_id = ruta_response.json()['id']
        print(f"  1. Created ruta: {ruta_payload['nombre']}")
        
        # 2. Create a modelo with this ruta
        marcas = requests.get(f"{BASE_URL}/api/marcas").json()
        tipos = requests.get(f"{BASE_URL}/api/tipos").json()
        entalles = requests.get(f"{BASE_URL}/api/entalles").json()
        telas = requests.get(f"{BASE_URL}/api/telas").json()
        hilos = requests.get(f"{BASE_URL}/api/hilos").json()
        
        modelo_payload = {
            "nombre": f"TEST_ModeloWorkflow_{uuid.uuid4().hex[:6]}",
            "marca_id": marcas[0]['id'] if marcas else "",
            "tipo_id": tipos[0]['id'] if tipos else "",
            "entalle_id": entalles[0]['id'] if entalles else "",
            "tela_id": telas[0]['id'] if telas else "",
            "hilo_id": hilos[0]['id'] if hilos else "",
            "ruta_produccion_id": ruta_id,
            "materiales": [],
            "servicios_ids": [SERVICIO_CORTE_ID, SERVICIO_COSTURA_ID]
        }
        modelo_response = requests.post(f"{BASE_URL}/api/modelos", json=modelo_payload)
        assert modelo_response.status_code == 200
        modelo_id = modelo_response.json()['id']
        print(f"  2. Created modelo: {modelo_payload['nombre']} with ruta")
        
        # 3. Create a registro with this modelo
        registro_payload = {
            "n_corte": f"TEST-{uuid.uuid4().hex[:6]}",
            "modelo_id": modelo_id,
            "curva": "A",
            "estado": "Corte",  # First state from ruta
            "urgente": False,
            "tallas": [],
            "distribucion_colores": []
        }
        registro_response = requests.post(f"{BASE_URL}/api/registros", json=registro_payload)
        assert registro_response.status_code == 200
        registro_id = registro_response.json()['id']
        print(f"  3. Created registro: {registro_payload['n_corte']}")
        
        # 4. Check estados disponibles for this registro
        estados_response = requests.get(f"{BASE_URL}/api/registros/{registro_id}/estados-disponibles")
        assert estados_response.status_code == 200
        estados_data = estados_response.json()
        assert estados_data['usa_ruta'] == True
        assert estados_data['ruta_nombre'] == ruta_payload['nombre']
        assert 'Corte' in estados_data['estados']
        assert 'Costura' in estados_data['estados']
        print(f"  4. Estados disponibles: {estados_data['estados']}")
        
        print("✓ Full workflow test passed")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/registros/{registro_id}")
        requests.delete(f"{BASE_URL}/api/modelos/{modelo_id}")
        requests.delete(f"{BASE_URL}/api/rutas-produccion/{ruta_id}")
    
    def test_ruta_deletion_blocked_by_modelo(self):
        """Test that ruta cannot be deleted if modelo uses it"""
        # Create ruta
        ruta_payload = {
            "nombre": f"TEST_BlockDelete_{uuid.uuid4().hex[:6]}",
            "descripcion": "",
            "etapas": [{"servicio_id": SERVICIO_CORTE_ID, "orden": 0}]
        }
        ruta_response = requests.post(f"{BASE_URL}/api/rutas-produccion", json=ruta_payload)
        assert ruta_response.status_code == 200
        ruta_id = ruta_response.json()['id']
        
        # Create modelo with this ruta
        marcas = requests.get(f"{BASE_URL}/api/marcas").json()
        tipos = requests.get(f"{BASE_URL}/api/tipos").json()
        entalles = requests.get(f"{BASE_URL}/api/entalles").json()
        telas = requests.get(f"{BASE_URL}/api/telas").json()
        hilos = requests.get(f"{BASE_URL}/api/hilos").json()
        
        modelo_payload = {
            "nombre": f"TEST_BlockModelo_{uuid.uuid4().hex[:6]}",
            "marca_id": marcas[0]['id'] if marcas else "",
            "tipo_id": tipos[0]['id'] if tipos else "",
            "entalle_id": entalles[0]['id'] if entalles else "",
            "tela_id": telas[0]['id'] if telas else "",
            "hilo_id": hilos[0]['id'] if hilos else "",
            "ruta_produccion_id": ruta_id,
            "materiales": [],
            "servicios_ids": []
        }
        modelo_response = requests.post(f"{BASE_URL}/api/modelos", json=modelo_payload)
        assert modelo_response.status_code == 200
        modelo_id = modelo_response.json()['id']
        
        # Try to delete ruta - should be blocked
        delete_response = requests.delete(f"{BASE_URL}/api/rutas-produccion/{ruta_id}")
        assert delete_response.status_code == 400
        assert "modelo" in delete_response.json().get('detail', '').lower()
        print("✓ Ruta deletion blocked when modelo uses it")
        
        # Cleanup - delete modelo first, then ruta
        requests.delete(f"{BASE_URL}/api/modelos/{modelo_id}")
        delete_after = requests.delete(f"{BASE_URL}/api/rutas-produccion/{ruta_id}")
        assert delete_after.status_code == 200
        print("✓ Ruta deleted after modelo removed")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
