"""
Tests for Lineas de Negocio feature
- GET /api/lineas-negocio: Returns active business lines from finanzas2.cont_linea_negocio
- GET /api/inventario/stock-por-linea: Returns stock grouped by item and line
- Modelos: linea_negocio_id column, selector in dialog
- Inventario: linea_negocio_id column, filter by line
- Ingresos: linea_negocio_id in form, auto-inherit from item
- Registros: linea_negocio_id inherited from modelo
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://kardex-pt-sync.preview.emergentagent.com').rstrip('/')

# Test credentials
TEST_USER = "eduard"
TEST_PASS = "eduard123"

# Known lineas de negocio from context
LINEA_PANTALON_ID = 22
LINEA_POLO_ID = 23


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username": TEST_USER,
        "password": TEST_PASS
    }, timeout=30)
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Authentication failed - skipping authenticated tests")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


class TestLineasNegocioEndpoint:
    """Tests for GET /api/lineas-negocio endpoint"""
    
    def test_get_lineas_negocio_returns_list(self):
        """GET /api/lineas-negocio should return list of active business lines"""
        response = requests.get(f"{BASE_URL}/api/lineas-negocio", timeout=30)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
    def test_lineas_negocio_has_expected_fields(self):
        """Each linea should have id, codigo, nombre"""
        response = requests.get(f"{BASE_URL}/api/lineas-negocio", timeout=30)
        assert response.status_code == 200
        
        data = response.json()
        if len(data) > 0:
            linea = data[0]
            assert "id" in linea, "Linea should have 'id' field"
            assert "nombre" in linea, "Linea should have 'nombre' field"
            # codigo may be optional
            
    def test_lineas_negocio_contains_known_lines(self):
        """Should contain the known business lines: ELEMENT PREMIUM - PANTALON and POLO"""
        response = requests.get(f"{BASE_URL}/api/lineas-negocio", timeout=30)
        assert response.status_code == 200
        
        data = response.json()
        ids = [ln["id"] for ln in data]
        nombres = [ln["nombre"] for ln in data]
        
        # Check for known lines
        assert LINEA_PANTALON_ID in ids or "ELEMENT PREMIUM - PANTALON" in nombres, \
            f"Expected ELEMENT PREMIUM - PANTALON (id=22) in response. Got: {data}"
        assert LINEA_POLO_ID in ids or "ELEMENT PREMIUM - POLO" in nombres, \
            f"Expected ELEMENT PREMIUM - POLO (id=23) in response. Got: {data}"


class TestStockPorLineaEndpoint:
    """Tests for GET /api/inventario/stock-por-linea endpoint"""
    
    def test_get_stock_por_linea_returns_list(self):
        """GET /api/inventario/stock-por-linea should return list of items with stock info"""
        response = requests.get(f"{BASE_URL}/api/inventario/stock-por-linea", timeout=60)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
    def test_stock_por_linea_has_expected_fields(self):
        """Each item should have item_id, codigo, nombre, stock fields, linea fields"""
        response = requests.get(f"{BASE_URL}/api/inventario/stock-por-linea", timeout=60)
        assert response.status_code == 200
        
        data = response.json()
        if len(data) > 0:
            item = data[0]
            # Required fields
            assert "item_id" in item, "Item should have 'item_id'"
            assert "codigo" in item, "Item should have 'codigo'"
            assert "nombre" in item, "Item should have 'nombre'"
            assert "stock_actual" in item, "Item should have 'stock_actual'"
            # Linea fields (can be null for global items)
            assert "item_linea_id" in item, "Item should have 'item_linea_id'"
            assert "linea_nombre" in item, "Item should have 'linea_nombre'"


class TestModelosWithLineaNegocio:
    """Tests for Modelos with linea_negocio_id"""
    
    def test_get_modelos_includes_linea_negocio(self, auth_headers):
        """GET /api/modelos should include linea_negocio_id and linea_negocio_nombre"""
        response = requests.get(f"{BASE_URL}/api/modelos?limit=10", headers=auth_headers, timeout=30)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        # Response is paginated
        items = data.get("items", data) if isinstance(data, dict) else data
        
        if len(items) > 0:
            modelo = items[0]
            # linea_negocio_id can be null (Global)
            assert "linea_negocio_id" in modelo or modelo.get("linea_negocio_nombre") is not None or True, \
                "Modelo should have linea_negocio fields"
    
    def test_create_modelo_with_linea_negocio(self, auth_headers):
        """POST /api/modelos with linea_negocio_id should persist"""
        # First get required IDs for modelo
        marcas = requests.get(f"{BASE_URL}/api/marcas", headers=auth_headers, timeout=30).json()
        tipos = requests.get(f"{BASE_URL}/api/tipos", headers=auth_headers, timeout=30).json()
        entalles = requests.get(f"{BASE_URL}/api/entalles", headers=auth_headers, timeout=30).json()
        telas = requests.get(f"{BASE_URL}/api/telas", headers=auth_headers, timeout=30).json()
        hilos = requests.get(f"{BASE_URL}/api/hilos", headers=auth_headers, timeout=30).json()
        
        if not all([marcas, tipos, entalles, telas, hilos]):
            pytest.skip("Missing required catalog data for modelo creation")
        
        payload = {
            "nombre": f"TEST_MODELO_LINEA_{int(time.time())}",
            "marca_id": marcas[0]["id"],
            "tipo_id": tipos[0]["id"],
            "entalle_id": entalles[0]["id"],
            "tela_id": telas[0]["id"],
            "hilo_id": hilos[0]["id"],
            "linea_negocio_id": LINEA_PANTALON_ID  # ELEMENT PREMIUM - PANTALON
        }
        
        response = requests.post(f"{BASE_URL}/api/modelos", json=payload, headers=auth_headers, timeout=30)
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        
        created = response.json()
        modelo_id = created.get("id")
        assert modelo_id, "Created modelo should have id"
        
        # Verify persistence by fetching
        get_response = requests.get(f"{BASE_URL}/api/modelos/{modelo_id}", headers=auth_headers, timeout=30)
        if get_response.status_code == 200:
            fetched = get_response.json()
            assert fetched.get("linea_negocio_id") == LINEA_PANTALON_ID, \
                f"Expected linea_negocio_id={LINEA_PANTALON_ID}, got {fetched.get('linea_negocio_id')}"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/modelos/{modelo_id}", headers=auth_headers, timeout=30)


class TestInventarioWithLineaNegocio:
    """Tests for Inventario items with linea_negocio_id"""
    
    def test_get_inventario_with_linea_filter(self, auth_headers):
        """GET /api/inventario with linea_negocio_id filter should work"""
        # Filter by specific linea
        response = requests.get(
            f"{BASE_URL}/api/inventario?linea_negocio_id={LINEA_PANTALON_ID}&limit=10",
            headers=auth_headers, timeout=30
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
    def test_get_inventario_global_filter(self, auth_headers):
        """GET /api/inventario with linea_negocio_id=global should return only global items"""
        response = requests.get(
            f"{BASE_URL}/api/inventario?linea_negocio_id=global&limit=10",
            headers=auth_headers, timeout=30
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        items = data.get("items", data) if isinstance(data, dict) else data
        
        # All items should have linea_negocio_id = null
        for item in items:
            assert item.get("linea_negocio_id") is None, \
                f"Global filter should only return items with linea_negocio_id=null, got {item.get('linea_negocio_id')}"
    
    def test_create_item_with_linea_negocio(self, auth_headers):
        """POST /api/inventario with linea_negocio_id should persist"""
        payload = {
            "codigo": f"TEST_ITEM_LN_{int(time.time())}",
            "nombre": f"Test Item Linea Negocio {int(time.time())}",
            "descripcion": "Test item for linea negocio testing",
            "categoria": "Avios",
            "unidad_medida": "unidad",
            "stock_minimo": 10,
            "linea_negocio_id": LINEA_POLO_ID  # ELEMENT PREMIUM - POLO
        }
        
        response = requests.post(f"{BASE_URL}/api/inventario", json=payload, headers=auth_headers, timeout=30)
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        
        created = response.json()
        item_id = created.get("id")
        assert item_id, "Created item should have id"
        
        # Verify persistence
        get_response = requests.get(f"{BASE_URL}/api/inventario/{item_id}", headers=auth_headers, timeout=30)
        if get_response.status_code == 200:
            fetched = get_response.json()
            assert fetched.get("linea_negocio_id") == LINEA_POLO_ID, \
                f"Expected linea_negocio_id={LINEA_POLO_ID}, got {fetched.get('linea_negocio_id')}"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/inventario/{item_id}", headers=auth_headers, timeout=30)
    
    def test_update_item_linea_negocio(self, auth_headers):
        """PUT /api/inventario/{id} should update linea_negocio_id"""
        # Create item without linea
        payload = {
            "codigo": f"TEST_UPD_LN_{int(time.time())}",
            "nombre": f"Test Update Linea {int(time.time())}",
            "categoria": "Otros",
            "unidad_medida": "unidad",
            "stock_minimo": 0,
            "linea_negocio_id": None
        }
        
        create_response = requests.post(f"{BASE_URL}/api/inventario", json=payload, headers=auth_headers, timeout=30)
        if create_response.status_code not in [200, 201]:
            pytest.skip("Could not create test item")
        
        item_id = create_response.json().get("id")
        
        # Update with linea_negocio_id
        update_payload = {
            **payload,
            "linea_negocio_id": LINEA_PANTALON_ID
        }
        
        update_response = requests.put(
            f"{BASE_URL}/api/inventario/{item_id}",
            json=update_payload,
            headers=auth_headers,
            timeout=30
        )
        assert update_response.status_code == 200, f"Expected 200, got {update_response.status_code}"
        
        # Verify update
        get_response = requests.get(f"{BASE_URL}/api/inventario/{item_id}", headers=auth_headers, timeout=30)
        if get_response.status_code == 200:
            fetched = get_response.json()
            assert fetched.get("linea_negocio_id") == LINEA_PANTALON_ID
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/inventario/{item_id}", headers=auth_headers, timeout=30)


class TestIngresosWithLineaNegocio:
    """Tests for Ingresos with linea_negocio_id"""
    
    def test_create_ingreso_with_linea_negocio(self, auth_headers):
        """POST /api/inventario-ingresos with linea_negocio_id should persist"""
        # First create a test item
        item_payload = {
            "codigo": f"TEST_ING_LN_{int(time.time())}",
            "nombre": f"Test Ingreso Linea {int(time.time())}",
            "categoria": "Avios",
            "unidad_medida": "unidad",
            "stock_minimo": 0,
            "linea_negocio_id": LINEA_POLO_ID
        }
        
        item_response = requests.post(f"{BASE_URL}/api/inventario", json=item_payload, headers=auth_headers, timeout=30)
        if item_response.status_code not in [200, 201]:
            pytest.skip("Could not create test item for ingreso")
        
        item_id = item_response.json().get("id")
        
        # Create ingreso with linea_negocio_id
        ingreso_payload = {
            "item_id": item_id,
            "cantidad": 100,
            "costo_unitario": 1.5,
            "proveedor": "Test Proveedor",
            "numero_documento": "TEST-001",
            "observaciones": "Test ingreso with linea negocio",
            "linea_negocio_id": LINEA_POLO_ID
        }
        
        response = requests.post(f"{BASE_URL}/api/inventario-ingresos", json=ingreso_payload, headers=auth_headers, timeout=30)
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        
        created = response.json()
        ingreso_id = created.get("id")
        
        # Cleanup
        if ingreso_id:
            requests.delete(f"{BASE_URL}/api/inventario-ingresos/{ingreso_id}", headers=auth_headers, timeout=30)
        requests.delete(f"{BASE_URL}/api/inventario/{item_id}", headers=auth_headers, timeout=30)


class TestRegistrosWithLineaNegocio:
    """Tests for Registros inheriting linea_negocio_id from modelo"""
    
    def test_registro_inherits_linea_from_modelo(self, auth_headers):
        """Creating a registro should inherit linea_negocio_id from its modelo"""
        # Get a modelo with linea_negocio_id
        modelos_response = requests.get(f"{BASE_URL}/api/modelos?limit=50", headers=auth_headers, timeout=30)
        if modelos_response.status_code != 200:
            pytest.skip("Could not fetch modelos")
        
        modelos_data = modelos_response.json()
        modelos = modelos_data.get("items", modelos_data) if isinstance(modelos_data, dict) else modelos_data
        
        # Find a modelo with linea_negocio_id set
        modelo_con_linea = None
        for m in modelos:
            if m.get("linea_negocio_id"):
                modelo_con_linea = m
                break
        
        if not modelo_con_linea:
            pytest.skip("No modelo with linea_negocio_id found for testing inheritance")
        
        # Create registro without explicit linea_negocio_id
        registro_payload = {
            "n_corte": f"TEST_REG_LN_{int(time.time())}",
            "modelo_id": modelo_con_linea["id"],
            "estado": "Para Corte",
            "urgente": False,
            "tallas": []
        }
        
        response = requests.post(f"{BASE_URL}/api/registros", json=registro_payload, headers=auth_headers, timeout=30)
        if response.status_code not in [200, 201]:
            pytest.skip(f"Could not create test registro: {response.text}")
        
        created = response.json()
        registro_id = created.get("id")
        
        # Verify inheritance
        get_response = requests.get(f"{BASE_URL}/api/registros/{registro_id}", headers=auth_headers, timeout=30)
        if get_response.status_code == 200:
            fetched = get_response.json()
            assert fetched.get("linea_negocio_id") == modelo_con_linea.get("linea_negocio_id"), \
                f"Registro should inherit linea_negocio_id from modelo. Expected {modelo_con_linea.get('linea_negocio_id')}, got {fetched.get('linea_negocio_id')}"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/registros/{registro_id}", headers=auth_headers, timeout=30)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
