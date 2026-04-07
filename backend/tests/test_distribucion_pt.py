"""
Test suite for Distribucion de Producto Terminado (PT) module.
Tests: distribucion-pt, vinculos-odoo, conciliacion-odoo, product-templates, stock-inventories
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test registro ID with tallas (total=400): 4b5ef69c-192a-4ffb-87df-35e4ef5e4fcc
TEST_REGISTRO_ID = "4b5ef69c-192a-4ffb-87df-35e4ef5e4fcc"
# Ajuste Odoo disponible: odoo_id 9886
TEST_AJUSTE_ODOO_ID = 9886
# Productos Odoo: 1469 (UNICO), 2455 (ROEL)
TEST_PRODUCT_1 = 1469
TEST_PRODUCT_2 = 2455


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


@pytest.fixture(scope="module")
def auth_header(auth_token):
    """Auth header for requests"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestOdooProductTemplates:
    """Tests for GET /api/odoo/product-templates - Search products in ODS"""
    
    def test_search_products_by_name(self, auth_header):
        """Search products by name returns results"""
        response = requests.get(
            f"{BASE_URL}/api/odoo/product-templates?search=UNICO&limit=10",
            headers=auth_header
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} products matching 'UNICO'")
        if len(data) > 0:
            assert "odoo_id" in data[0]
            assert "name" in data[0]
    
    def test_search_products_by_id(self, auth_header):
        """Search products by ID returns results"""
        response = requests.get(
            f"{BASE_URL}/api/odoo/product-templates?search={TEST_PRODUCT_1}&limit=10",
            headers=auth_header
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} products matching ID {TEST_PRODUCT_1}")
    
    def test_search_products_empty_returns_list(self, auth_header):
        """Empty search returns default list"""
        response = requests.get(
            f"{BASE_URL}/api/odoo/product-templates?limit=5",
            headers=auth_header
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 5


class TestOdooStockInventories:
    """Tests for GET /api/odoo/stock-inventories - Filter stock adjustments"""
    
    def test_get_stock_inventories_produccion(self, auth_header):
        """Get stock inventories with x_es_ingreso_produccion=true"""
        response = requests.get(
            f"{BASE_URL}/api/odoo/stock-inventories?solo_produccion=true&limit=50",
            headers=auth_header
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} stock inventories for production")
        
        # Check structure
        if len(data) > 0:
            item = data[0]
            assert "odoo_id" in item
            assert "name" in item
            assert "disponible" in item
            assert "vinculado_a_registro" in item or item.get("disponible") is not None
    
    def test_get_stock_inventories_shows_availability(self, auth_header):
        """Stock inventories show if available or linked"""
        response = requests.get(
            f"{BASE_URL}/api/odoo/stock-inventories?solo_produccion=true&limit=50",
            headers=auth_header
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check that disponible field exists
        for item in data:
            assert "disponible" in item, f"Missing 'disponible' field in {item}"
            print(f"Ajuste {item['odoo_id']} ({item['name']}): disponible={item['disponible']}")


class TestDistribucionPT:
    """Tests for Distribucion PT endpoints"""
    
    def test_get_distribucion_pt(self, auth_header):
        """GET /api/registros/{id}/distribucion-pt returns total_producido, lineas, cuadra"""
        response = requests.get(
            f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/distribucion-pt",
            headers=auth_header
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Validate structure
        assert "registro_id" in data
        assert "total_producido" in data
        assert "total_distribuido" in data
        assert "cuadra" in data
        assert "lineas" in data
        assert isinstance(data["lineas"], list)
        
        print(f"Distribucion PT: total_producido={data['total_producido']}, total_distribuido={data['total_distribuido']}, cuadra={data['cuadra']}")
    
    def test_get_distribucion_pt_registro_not_found(self, auth_header):
        """GET distribucion-pt for non-existent registro returns 404"""
        response = requests.get(
            f"{BASE_URL}/api/registros/non-existent-id/distribucion-pt",
            headers=auth_header
        )
        assert response.status_code == 404
    
    def test_post_distribucion_pt_cantidad_no_cuadra(self, auth_header):
        """POST distribucion-pt rejects when sum != total_producido"""
        # First get total_producido
        get_resp = requests.get(
            f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/distribucion-pt",
            headers=auth_header
        )
        total_producido = get_resp.json().get("total_producido", 400)
        
        # Try to save with wrong sum
        wrong_sum = total_producido - 50  # Intentionally wrong
        response = requests.post(
            f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/distribucion-pt",
            headers=auth_header,
            json={
                "lineas": [
                    {"tipo_salida": "normal", "product_template_id_odoo": TEST_PRODUCT_1, "cantidad": wrong_sum}
                ]
            }
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        assert "no coincide" in response.json().get("detail", "").lower() or "total" in response.json().get("detail", "").lower()
        print(f"Correctly rejected: {response.json().get('detail')}")
    
    def test_post_distribucion_pt_cantidad_cero_o_negativa(self, auth_header):
        """POST distribucion-pt rejects cantidad <= 0"""
        response = requests.post(
            f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/distribucion-pt",
            headers=auth_header,
            json={
                "lineas": [
                    {"tipo_salida": "normal", "product_template_id_odoo": TEST_PRODUCT_1, "cantidad": 0}
                ]
            }
        )
        # Pydantic validation should reject cantidad <= 0
        assert response.status_code == 422 or response.status_code == 400
        print(f"Correctly rejected cantidad=0: status={response.status_code}")
    
    def test_post_distribucion_pt_producto_inexistente(self, auth_header):
        """POST distribucion-pt rejects non-existent product_template_id_odoo"""
        # Get total_producido first
        get_resp = requests.get(
            f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/distribucion-pt",
            headers=auth_header
        )
        total_producido = get_resp.json().get("total_producido", 400)
        
        response = requests.post(
            f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/distribucion-pt",
            headers=auth_header,
            json={
                "lineas": [
                    {"tipo_salida": "normal", "product_template_id_odoo": 999999999, "cantidad": total_producido}
                ]
            }
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        assert "no encontrado" in response.json().get("detail", "").lower() or "999999999" in response.json().get("detail", "")
        print(f"Correctly rejected non-existent product: {response.json().get('detail')}")
    
    def test_post_distribucion_pt_guarda_correctamente(self, auth_header):
        """POST distribucion-pt saves correctly when sum matches total_producido"""
        # Get total_producido
        get_resp = requests.get(
            f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/distribucion-pt",
            headers=auth_header
        )
        total_producido = get_resp.json().get("total_producido", 400)
        
        if total_producido <= 0:
            pytest.skip("Registro has no total_producido")
        
        # Split between two products
        cantidad_1 = int(total_producido * 0.6)
        cantidad_2 = total_producido - cantidad_1
        
        response = requests.post(
            f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/distribucion-pt",
            headers=auth_header,
            json={
                "lineas": [
                    {"tipo_salida": "normal", "product_template_id_odoo": TEST_PRODUCT_1, "cantidad": cantidad_1},
                    {"tipo_salida": "arreglo", "product_template_id_odoo": TEST_PRODUCT_2, "cantidad": cantidad_2}
                ]
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("ok") == True
        assert data.get("total_distribuido") == total_producido
        print(f"Saved distribucion: {cantidad_1} to product {TEST_PRODUCT_1}, {cantidad_2} to product {TEST_PRODUCT_2}")
        
        # Verify by GET
        verify_resp = requests.get(
            f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/distribucion-pt",
            headers=auth_header
        )
        verify_data = verify_resp.json()
        assert verify_data["cuadra"] == True
        assert len(verify_data["lineas"]) == 2
    
    def test_delete_distribucion_pt(self, auth_header):
        """DELETE /api/registros/{id}/distribucion-pt removes all distribution"""
        response = requests.delete(
            f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/distribucion-pt",
            headers=auth_header
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert response.json().get("ok") == True
        
        # Verify deletion
        verify_resp = requests.get(
            f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/distribucion-pt",
            headers=auth_header
        )
        verify_data = verify_resp.json()
        assert len(verify_data["lineas"]) == 0
        assert verify_data["total_distribuido"] == 0
        print("Distribucion deleted successfully")


class TestVinculosOdoo:
    """Tests for Vinculos Odoo endpoints"""
    
    def test_get_vinculos_odoo(self, auth_header):
        """GET /api/registros/{id}/vinculos-odoo returns vinculos with ajuste info"""
        response = requests.get(
            f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/vinculos-odoo",
            headers=auth_header
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} vinculos for registro")
        
        # Check structure if any vinculos exist
        if len(data) > 0:
            vinculo = data[0]
            assert "id" in vinculo
            assert "stock_inventory_odoo_id" in vinculo
            assert "ajuste_nombre" in vinculo or vinculo.get("stock_inventory_odoo_id") is not None
    
    def test_post_vincular_ajuste_odoo(self, auth_header):
        """POST /api/registros/{id}/vinculos-odoo links an Odoo adjustment"""
        # First, clean up any existing vinculo
        vinculos_resp = requests.get(
            f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/vinculos-odoo",
            headers=auth_header
        )
        for v in vinculos_resp.json():
            if v.get("stock_inventory_odoo_id") == TEST_AJUSTE_ODOO_ID:
                requests.delete(
                    f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/vinculos-odoo/{v['id']}",
                    headers=auth_header
                )
        
        # Now link the adjustment
        response = requests.post(
            f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/vinculos-odoo",
            headers=auth_header,
            json={"stock_inventory_odoo_id": TEST_AJUSTE_ODOO_ID}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("ok") == True
        print(f"Linked ajuste {TEST_AJUSTE_ODOO_ID}: {data.get('ajuste_nombre')}")
    
    def test_post_vincular_ajuste_ya_vinculado_mismo_registro(self, auth_header):
        """POST vinculos-odoo rejects linking same adjustment twice to same registro"""
        # Try to link again
        response = requests.post(
            f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/vinculos-odoo",
            headers=auth_header,
            json={"stock_inventory_odoo_id": TEST_AJUSTE_ODOO_ID}
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        assert "ya esta vinculado" in response.json().get("detail", "").lower()
        print(f"Correctly rejected duplicate: {response.json().get('detail')}")
    
    def test_post_vincular_ajuste_inexistente(self, auth_header):
        """POST vinculos-odoo rejects non-existent adjustment"""
        response = requests.post(
            f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/vinculos-odoo",
            headers=auth_header,
            json={"stock_inventory_odoo_id": 999999999}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print(f"Correctly rejected non-existent ajuste: {response.json().get('detail')}")
    
    def test_delete_desvincular_ajuste(self, auth_header):
        """DELETE /api/registros/{id}/vinculos-odoo/{vinculo_id} unlinks correctly"""
        # Get current vinculos
        vinculos_resp = requests.get(
            f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/vinculos-odoo",
            headers=auth_header
        )
        vinculos = vinculos_resp.json()
        
        if len(vinculos) == 0:
            # Link one first
            requests.post(
                f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/vinculos-odoo",
                headers=auth_header,
                json={"stock_inventory_odoo_id": TEST_AJUSTE_ODOO_ID}
            )
            vinculos_resp = requests.get(
                f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/vinculos-odoo",
                headers=auth_header
            )
            vinculos = vinculos_resp.json()
        
        if len(vinculos) > 0:
            vinculo_id = vinculos[0]["id"]
            response = requests.delete(
                f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/vinculos-odoo/{vinculo_id}",
                headers=auth_header
            )
            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
            assert response.json().get("ok") == True
            print(f"Unlinked vinculo {vinculo_id}")


class TestConciliacionOdoo:
    """Tests for Conciliacion Odoo endpoint"""
    
    def test_get_conciliacion_odoo(self, auth_header):
        """GET /api/registros/{id}/conciliacion-odoo returns detail with esperado, ingresado, pendiente, estado"""
        # First, set up some distribution
        get_resp = requests.get(
            f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/distribucion-pt",
            headers=auth_header
        )
        total_producido = get_resp.json().get("total_producido", 400)
        
        if total_producido > 0:
            # Save distribution
            requests.post(
                f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/distribucion-pt",
                headers=auth_header,
                json={
                    "lineas": [
                        {"tipo_salida": "normal", "product_template_id_odoo": TEST_PRODUCT_1, "cantidad": total_producido}
                    ]
                }
            )
        
        # Get conciliacion
        response = requests.get(
            f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/conciliacion-odoo",
            headers=auth_header
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Validate structure
        assert "registro_id" in data
        assert "total_producido" in data
        assert "total_esperado" in data
        assert "total_ingresado" in data
        assert "total_pendiente" in data
        assert "estado" in data
        assert "detalle" in data
        assert isinstance(data["detalle"], list)
        
        print(f"Conciliacion: esperado={data['total_esperado']}, ingresado={data['total_ingresado']}, pendiente={data['total_pendiente']}, estado={data['estado']}")
        
        # Check detalle structure
        if len(data["detalle"]) > 0:
            item = data["detalle"][0]
            assert "product_template_id_odoo" in item
            assert "esperado" in item
            assert "ingresado" in item
            assert "pendiente" in item
            assert "estado" in item
    
    def test_conciliacion_estado_sin_distribucion(self, auth_header):
        """Conciliacion returns SIN_DISTRIBUCION when no distribution exists"""
        # Delete distribution first
        requests.delete(
            f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/distribucion-pt",
            headers=auth_header
        )
        
        response = requests.get(
            f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/conciliacion-odoo",
            headers=auth_header
        )
        assert response.status_code == 200
        data = response.json()
        assert data["estado"] == "SIN_DISTRIBUCION"
        print(f"Estado correctly shows SIN_DISTRIBUCION when no distribution")


class TestUniqueConstraintVinculos:
    """Tests for UNIQUE constraint on stock_inventory_odoo_id in vinculos"""
    
    def test_unique_constraint_different_registros(self, auth_header):
        """POST vinculos-odoo rejects linking same adjustment to different registro (UNIQUE constraint)"""
        # First, link to test registro
        # Clean up first
        vinculos_resp = requests.get(
            f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/vinculos-odoo",
            headers=auth_header
        )
        for v in vinculos_resp.json():
            if v.get("stock_inventory_odoo_id") == TEST_AJUSTE_ODOO_ID:
                requests.delete(
                    f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/vinculos-odoo/{v['id']}",
                    headers=auth_header
                )
        
        # Link to test registro
        link_resp = requests.post(
            f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/vinculos-odoo",
            headers=auth_header,
            json={"stock_inventory_odoo_id": TEST_AJUSTE_ODOO_ID}
        )
        
        if link_resp.status_code != 200:
            pytest.skip(f"Could not link ajuste to test registro: {link_resp.text}")
        
        # Get another registro to test with
        registros_resp = requests.get(
            f"{BASE_URL}/api/registros?limit=10",
            headers=auth_header
        )
        registros_data = registros_resp.json()
        # Handle both list and dict with 'items' key
        registros = registros_data.get("items", registros_data) if isinstance(registros_data, dict) else registros_data
        other_registro = None
        for r in registros:
            if isinstance(r, dict) and r.get("id") != TEST_REGISTRO_ID:
                other_registro = r
                break
        
        if not other_registro:
            # Clean up and skip
            vinculos_resp = requests.get(
                f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/vinculos-odoo",
                headers=auth_header
            )
            for v in vinculos_resp.json():
                if v.get("stock_inventory_odoo_id") == TEST_AJUSTE_ODOO_ID:
                    requests.delete(
                        f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/vinculos-odoo/{v['id']}",
                        headers=auth_header
                    )
            pytest.skip("No other registro found to test UNIQUE constraint")
        
        # Try to link same ajuste to different registro
        response = requests.post(
            f"{BASE_URL}/api/registros/{other_registro['id']}/vinculos-odoo",
            headers=auth_header,
            json={"stock_inventory_odoo_id": TEST_AJUSTE_ODOO_ID}
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        detail = response.json().get("detail", "")
        assert "ya esta vinculado" in detail.lower() or TEST_REGISTRO_ID in detail
        print(f"UNIQUE constraint working: {detail}")
        
        # Clean up
        vinculos_resp = requests.get(
            f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/vinculos-odoo",
            headers=auth_header
        )
        for v in vinculos_resp.json():
            if v.get("stock_inventory_odoo_id") == TEST_AJUSTE_ODOO_ID:
                requests.delete(
                    f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/vinculos-odoo/{v['id']}",
                    headers=auth_header
                )


class TestCleanup:
    """Cleanup after tests"""
    
    def test_cleanup_distribucion(self, auth_header):
        """Clean up test data"""
        # Delete distribution
        requests.delete(
            f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/distribucion-pt",
            headers=auth_header
        )
        
        # Delete vinculos
        vinculos_resp = requests.get(
            f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/vinculos-odoo",
            headers=auth_header
        )
        for v in vinculos_resp.json():
            requests.delete(
                f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/vinculos-odoo/{v['id']}",
                headers=auth_header
            )
        
        print("Cleanup completed")
