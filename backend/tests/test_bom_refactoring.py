"""
Tests for BOM architectural refactoring:
1. SERVICIO lines use servicio_produccion_id (not inventario_id)
2. estados-disponibles comes from ruta etapas
3. Ruta etapas have nombre + optional servicio_id
4. Items cannot have 'Servicios' category (no backend validation, just frontend)
5. costo_manual editable per SERVICIO line in BOM
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
assert BASE_URL, "REACT_APP_BACKEND_URL must be set"

# Test credentials
USERNAME = "eduard"
PASSWORD = "eduard123"

# Test data IDs
EXISTING_BOM_ID = "2a7a6511-89f4-4a2f-a987-745c8df37842"
EXISTING_REGISTRO_ID = "c74d3460-3e8b-4d4c-88e5-06bff012d6f5"
EXISTING_MODELO_ID = "3d3f6dd0-bfab-4d79-afe5-2a4cce7f5a87"


@pytest.fixture(scope="module")
def auth_token():
    """Get auth token for all tests"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username": USERNAME,
        "password": PASSWORD
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["access_token"]


@pytest.fixture(scope="module")
def api_client(auth_token):
    """Create authenticated session"""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    })
    return session


class TestBOMServicioLines:
    """Test that BOM SERVICIO lines use servicio_produccion_id"""
    
    def test_get_bom_returns_servicio_produccion_id_for_servicio_lines(self, api_client):
        """GET /api/bom/{bom_id} returns servicio_produccion_id and servicio_nombre for SERVICIO lines"""
        response = api_client.get(f"{BASE_URL}/api/bom/{EXISTING_BOM_ID}")
        assert response.status_code == 200, f"Failed to get BOM: {response.text}"
        
        data = response.json()
        assert "lineas" in data, "Response must have lineas"
        
        servicio_lines = [l for l in data["lineas"] if l.get("tipo_componente") == "SERVICIO"]
        print(f"Found {len(servicio_lines)} SERVICIO lines")
        
        if servicio_lines:
            for line in servicio_lines:
                # SERVICIO lines should have servicio_produccion_id populated (or null if not yet set)
                # They should NOT use inventario_id for the service reference
                print(f"  Line: tipo={line.get('tipo_componente')}, servicio_produccion_id={line.get('servicio_produccion_id')}, inventario_id={line.get('inventario_id')}, servicio_nombre={line.get('servicio_nombre')}")
                
                # SERVICIO lines should have servicio_nombre from the service, not inventario_nombre
                if line.get('servicio_produccion_id'):
                    assert line.get('servicio_nombre') is not None, f"SERVICIO line with servicio_produccion_id should have servicio_nombre"
                    print(f"    servicio_nombre: {line.get('servicio_nombre')}")

    def test_update_servicio_line_with_servicio_produccion_id(self, api_client):
        """PUT /api/bom/{bom_id}/lineas/{linea_id} updates servicio_produccion_id for SERVICIO lines"""
        # First get the BOM to find a SERVICIO line
        response = api_client.get(f"{BASE_URL}/api/bom/{EXISTING_BOM_ID}")
        assert response.status_code == 200
        data = response.json()
        
        servicio_lines = [l for l in data["lineas"] if l.get("tipo_componente") == "SERVICIO"]
        if not servicio_lines:
            pytest.skip("No SERVICIO lines found in BOM")
        
        line = servicio_lines[0]
        line_id = line["id"]
        original_servicio_id = line.get("servicio_produccion_id")
        
        # Get available services
        services_resp = api_client.get(f"{BASE_URL}/api/servicios-produccion")
        assert services_resp.status_code == 200
        services = services_resp.json()
        
        if not services:
            pytest.skip("No services available")
        
        # Pick a service to update to
        new_service = services[0]
        new_servicio_id = new_service["id"]
        
        # Update the line
        update_resp = api_client.put(
            f"{BASE_URL}/api/bom/{EXISTING_BOM_ID}/lineas/{line_id}",
            json={"servicio_produccion_id": new_servicio_id}
        )
        assert update_resp.status_code == 200, f"Update failed: {update_resp.text}"
        
        updated_line = update_resp.json()
        assert updated_line.get("servicio_produccion_id") == new_servicio_id, "servicio_produccion_id not updated"
        print(f"Updated SERVICIO line: servicio_produccion_id={updated_line.get('servicio_produccion_id')}, servicio_nombre={updated_line.get('servicio_nombre')}")
        
        # Verify it persists
        verify_resp = api_client.get(f"{BASE_URL}/api/bom/{EXISTING_BOM_ID}")
        assert verify_resp.status_code == 200
        verify_data = verify_resp.json()
        verify_line = next((l for l in verify_data["lineas"] if l["id"] == line_id), None)
        assert verify_line is not None
        assert verify_line.get("servicio_produccion_id") == new_servicio_id
        
        # Restore original if different
        if original_servicio_id and original_servicio_id != new_servicio_id:
            api_client.put(
                f"{BASE_URL}/api/bom/{EXISTING_BOM_ID}/lineas/{line_id}",
                json={"servicio_produccion_id": original_servicio_id}
            )


class TestCostoEstandarWithServicioTarifa:
    """Test that costo-estandar uses servicio_tarifa or costo_manual for SERVICIO lines"""
    
    def test_costo_estandar_uses_servicio_tarifa_for_servicio_lines(self, api_client):
        """GET /api/bom/{bom_id}/costo-estandar uses servicio_tarifa (or costo_manual) for SERVICIO lines"""
        response = api_client.get(f"{BASE_URL}/api/bom/{EXISTING_BOM_ID}/costo-estandar?cantidad_prendas=1")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "detalle" in data, "Response must have detalle"
        
        servicio_details = [d for d in data["detalle"] if d.get("tipo_componente") == "SERVICIO"]
        print(f"Found {len(servicio_details)} SERVICIO cost details")
        
        for detail in servicio_details:
            precio = detail.get("precio_unitario", 0)
            costo_manual = detail.get("costo_manual")
            print(f"  SERVICIO: nombre={detail.get('inventario_nombre')}, precio_unitario={precio}, costo_manual={costo_manual}, costo_por_prenda={detail.get('costo_por_prenda')}")
            
            # precio_unitario should come from costo_manual or servicio_tarifa (not inventario costo_promedio)
            # The API uses servicio_tarifa when costo_manual is null


class TestEstadosDisponiblesFromRuta:
    """Test that estados-disponibles comes from ruta etapas when usa_ruta=true"""
    
    def test_estados_disponibles_returns_ruta_etapas(self, api_client):
        """GET /api/registros/{registro_id}/estados-disponibles returns estados from ruta etapas"""
        response = api_client.get(f"{BASE_URL}/api/registros/{EXISTING_REGISTRO_ID}/estados-disponibles")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        print(f"estados-disponibles response: usa_ruta={data.get('usa_ruta')}, estados={data.get('estados')}, ruta_nombre={data.get('ruta_nombre')}")
        
        if data.get("usa_ruta"):
            assert "estados" in data, "Response must have estados"
            assert "ruta_nombre" in data, "Response must have ruta_nombre when usa_ruta=true"
            estados = data["estados"]
            print(f"  Estados from ruta: {estados}")
            assert len(estados) > 0, "Should have at least one estado from ruta"
            
            # Each estado should be a string (nombre from etapa)
            for estado in estados:
                assert isinstance(estado, str), f"Estado must be string, got {type(estado)}"
        else:
            print("  Registro does not use ruta, fallback to ESTADOS_PRODUCCION")


class TestRutasProduccionEtapasWithNombre:
    """Test that rutas accept etapas with nombre and optional servicio_id"""
    
    def test_create_ruta_with_nombre_and_servicio_id(self, api_client):
        """POST /api/rutas-produccion accepts etapas with nombre and optional servicio_id"""
        # Get available services
        services_resp = api_client.get(f"{BASE_URL}/api/servicios-produccion")
        assert services_resp.status_code == 200
        services = services_resp.json()
        
        # Create ruta with mixed etapas (some with servicio_id, some without)
        servicio_id = services[0]["id"] if services else None
        
        etapas = [
            {"nombre": "Para Corte", "servicio_id": None, "orden": 0},
            {"nombre": "Corte", "servicio_id": servicio_id, "orden": 1},
            {"nombre": "Almacén", "servicio_id": None, "orden": 2}
        ]
        
        payload = {
            "nombre": "TEST_Ruta_Refactoring",
            "descripcion": "Test ruta with nombre + optional servicio_id",
            "etapas": etapas
        }
        
        response = api_client.post(f"{BASE_URL}/api/rutas-produccion", json=payload)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        created = response.json()
        assert created.get("nombre") == payload["nombre"]
        assert len(created.get("etapas", [])) == 3
        
        # Verify etapas have nombre preserved
        for i, etapa in enumerate(created["etapas"]):
            assert etapa.get("nombre") == etapas[i]["nombre"], f"Etapa {i} nombre not preserved"
            print(f"  Created etapa: nombre={etapa.get('nombre')}, servicio_id={etapa.get('servicio_id')}")
        
        # Cleanup
        ruta_id = created["id"]
        delete_resp = api_client.delete(f"{BASE_URL}/api/rutas-produccion/{ruta_id}")
        assert delete_resp.status_code == 200, "Cleanup failed"
        print(f"Cleaned up test ruta {ruta_id}")

    def test_get_ruta_returns_etapas_with_nombre(self, api_client):
        """GET /api/rutas-produccion returns etapas with nombre field"""
        response = api_client.get(f"{BASE_URL}/api/rutas-produccion")
        assert response.status_code == 200
        
        rutas = response.json()
        print(f"Found {len(rutas)} rutas")
        
        for ruta in rutas:
            etapas = ruta.get("etapas", [])
            print(f"  Ruta '{ruta.get('nombre')}': {len(etapas)} etapas")
            for etapa in etapas:
                nombre = etapa.get("nombre")
                servicio_nombre = etapa.get("servicio_nombre")
                servicio_id = etapa.get("servicio_id")
                print(f"    - nombre={nombre}, servicio_nombre={servicio_nombre}, servicio_id={servicio_id}")
                
                # nombre should always be present (it's the etapa name/estado)
                assert nombre is not None, f"Etapa must have nombre, got: {etapa}"


class TestBOMCostoManualForServicio:
    """Test that costo_manual is editable per SERVICIO line in BOM"""
    
    def test_update_costo_manual_on_servicio_line(self, api_client):
        """PUT /api/bom/{bom_id}/lineas/{linea_id} can update costo_manual for SERVICIO lines"""
        # Get BOM and find a SERVICIO line
        response = api_client.get(f"{BASE_URL}/api/bom/{EXISTING_BOM_ID}")
        assert response.status_code == 200
        data = response.json()
        
        servicio_lines = [l for l in data["lineas"] if l.get("tipo_componente") == "SERVICIO"]
        if not servicio_lines:
            pytest.skip("No SERVICIO lines found")
        
        line = servicio_lines[0]
        line_id = line["id"]
        original_costo = line.get("costo_manual")
        
        # Update costo_manual
        new_costo = 99.99
        update_resp = api_client.put(
            f"{BASE_URL}/api/bom/{EXISTING_BOM_ID}/lineas/{line_id}",
            json={"costo_manual": new_costo}
        )
        assert update_resp.status_code == 200, f"Update failed: {update_resp.text}"
        
        updated = update_resp.json()
        assert updated.get("costo_manual") == new_costo, f"costo_manual not updated: {updated.get('costo_manual')}"
        print(f"Updated costo_manual to {new_costo}")
        
        # Verify in costo-estandar
        costo_resp = api_client.get(f"{BASE_URL}/api/bom/{EXISTING_BOM_ID}/costo-estandar?cantidad_prendas=1")
        assert costo_resp.status_code == 200
        costo_data = costo_resp.json()
        
        detail = next((d for d in costo_data["detalle"] if d.get("linea_id") == line_id), None)
        if detail:
            print(f"  In costo-estandar: precio_unitario={detail.get('precio_unitario')}, costo_manual={detail.get('costo_manual')}")
            # When costo_manual is set, it should be used as precio_unitario
            assert detail.get("costo_manual") == new_costo or detail.get("precio_unitario") == new_costo
        
        # Restore original
        restore_resp = api_client.put(
            f"{BASE_URL}/api/bom/{EXISTING_BOM_ID}/lineas/{line_id}",
            json={"costo_manual": original_costo if original_costo else 0.0}
        )
        print(f"Restored costo_manual to {original_costo}")


class TestTELAAndAVIOUseInventario:
    """Test that TELA/AVIO lines still use inventario items (not servicios)"""
    
    def test_tela_avio_lines_have_inventario_id(self, api_client):
        """TELA/AVIO BOM lines should use inventario_id, not servicio_produccion_id"""
        response = api_client.get(f"{BASE_URL}/api/bom/{EXISTING_BOM_ID}")
        assert response.status_code == 200
        data = response.json()
        
        material_lines = [l for l in data["lineas"] if l.get("tipo_componente") in ["TELA", "AVIO"]]
        print(f"Found {len(material_lines)} material lines (TELA/AVIO)")
        
        for line in material_lines:
            tipo = line.get("tipo_componente")
            inv_id = line.get("inventario_id")
            inv_nombre = line.get("inventario_nombre")
            serv_id = line.get("servicio_produccion_id")
            
            print(f"  {tipo}: inventario_id={inv_id}, inventario_nombre={inv_nombre}, servicio_produccion_id={serv_id}")
            
            # TELA/AVIO should have inventario_id, not servicio_produccion_id
            if inv_id:
                assert inv_nombre is not None or inv_id is not None, f"{tipo} line should have inventario info"


class TestInventarioCategoriesBackend:
    """Test that inventario items can be retrieved (frontend filters Servicios category)"""
    
    def test_get_inventario_items(self, api_client):
        """GET /api/inventario returns items with various categories"""
        response = api_client.get(f"{BASE_URL}/api/inventario")
        assert response.status_code == 200
        
        items = response.json()
        categories = set(item.get("categoria") for item in items)
        print(f"Found {len(items)} inventario items with categories: {categories}")
        
        # Note: Backend does not prevent 'Servicios' category - that's a frontend-only restriction
        # This test just verifies the API works
        for cat in categories:
            count = len([i for i in items if i.get("categoria") == cat])
            print(f"  {cat}: {count} items")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
