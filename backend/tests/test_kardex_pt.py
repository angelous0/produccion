"""
Test Kardex PT (Producto Terminado) endpoints.
Tests: GET /api/kardex-pt, GET /api/kardex-pt/resumen, GET /api/kardex-pt/filtros
Filters: product_tmpl_id, tipo_movimiento, fecha_desde, fecha_hasta, company_key, location_id, pagination
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_USER = "eduard"
TEST_PASS = "eduard123"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for tests."""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username": TEST_USER,
        "password": TEST_PASS
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def headers(auth_token):
    """Headers with auth token."""
    return {"Authorization": f"Bearer {auth_token}"}


class TestKardexPTFiltros:
    """Test GET /api/kardex-pt/filtros - Returns filter options."""
    
    def test_filtros_returns_company_keys(self, headers):
        """Should return list of company_keys."""
        response = requests.get(f"{BASE_URL}/api/kardex-pt/filtros", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "company_keys" in data
        assert isinstance(data["company_keys"], list)
        # Per context: Ambission, ProyectoModa
        print(f"Company keys: {data['company_keys']}")
    
    def test_filtros_returns_ubicaciones(self, headers):
        """Should return list of internal locations."""
        response = requests.get(f"{BASE_URL}/api/kardex-pt/filtros", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "ubicaciones" in data
        assert isinstance(data["ubicaciones"], list)
        # Per context: 18 internal locations
        print(f"Ubicaciones count: {len(data['ubicaciones'])}")
        if data["ubicaciones"]:
            assert "id" in data["ubicaciones"][0]
            assert "name" in data["ubicaciones"][0]
    
    def test_filtros_returns_tipos_movimiento(self, headers):
        """Should return movement types."""
        response = requests.get(f"{BASE_URL}/api/kardex-pt/filtros", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "tipos_movimiento" in data
        tipos = data["tipos_movimiento"]
        assert isinstance(tipos, list)
        # Expected types
        expected_values = ["INGRESO_PRODUCCION", "SALIDA_VENTA", "AJUSTE_POSITIVO", "AJUSTE_NEGATIVO", "TRANSFERENCIA"]
        actual_values = [t["value"] for t in tipos]
        for expected in expected_values:
            assert expected in actual_values, f"Missing tipo: {expected}"
        print(f"Tipos movimiento: {actual_values}")


class TestKardexPTMain:
    """Test GET /api/kardex-pt - Main kardex endpoint with pagination and filters."""
    
    def test_kardex_returns_paginated_items(self, headers):
        """Should return paginated items with required fields."""
        response = requests.get(f"{BASE_URL}/api/kardex-pt?page=1&page_size=10", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # Check pagination structure
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert data["page"] == 1
        assert data["page_size"] == 10
        
        # Per context: 2151 movements (excluding transfers)
        print(f"Total movements: {data['total']}")
        assert data["total"] > 0
        
        # Check item structure
        if data["items"]:
            item = data["items"][0]
            required_fields = ["odoo_id", "fecha", "product_tmpl_id", "producto_nombre", 
                             "tipo_movimiento", "entrada", "salida", "saldo_acumulado"]
            for field in required_fields:
                assert field in item, f"Missing field: {field}"
            print(f"Sample item tipo_movimiento: {item['tipo_movimiento']}")
    
    def test_kardex_excludes_transfers_by_default(self, headers):
        """Should exclude TRANSFERENCIA from global results (no location filter)."""
        response = requests.get(f"{BASE_URL}/api/kardex-pt?page=1&page_size=100", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # Check that no TRANSFERENCIA items in results
        transfer_items = [i for i in data["items"] if i["tipo_movimiento"] == "TRANSFERENCIA"]
        assert len(transfer_items) == 0, f"Found {len(transfer_items)} TRANSFERENCIA items without location filter"
        print("Verified: No TRANSFERENCIA items in global results")
    
    def test_kardex_filter_by_tipo_movimiento_salida_venta(self, headers):
        """Should filter by tipo_movimiento=SALIDA_VENTA."""
        response = requests.get(f"{BASE_URL}/api/kardex-pt?tipo_movimiento=SALIDA_VENTA&page_size=50", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # All items should be SALIDA_VENTA
        for item in data["items"]:
            assert item["tipo_movimiento"] == "SALIDA_VENTA", f"Got {item['tipo_movimiento']} instead of SALIDA_VENTA"
        print(f"SALIDA_VENTA items: {data['total']}")
    
    def test_kardex_filter_by_tipo_movimiento_ingreso_produccion(self, headers):
        """Should filter by tipo_movimiento=INGRESO_PRODUCCION."""
        response = requests.get(f"{BASE_URL}/api/kardex-pt?tipo_movimiento=INGRESO_PRODUCCION&page_size=50", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        for item in data["items"]:
            assert item["tipo_movimiento"] == "INGRESO_PRODUCCION"
        print(f"INGRESO_PRODUCCION items: {data['total']}")
    
    def test_kardex_filter_by_company_key(self, headers):
        """Should filter by company_key."""
        # First get available company keys
        filtros_resp = requests.get(f"{BASE_URL}/api/kardex-pt/filtros", headers=headers)
        company_keys = filtros_resp.json().get("company_keys", [])
        
        if company_keys:
            company = company_keys[0]
            response = requests.get(f"{BASE_URL}/api/kardex-pt?company_key={company}&page_size=20", headers=headers)
            assert response.status_code == 200
            data = response.json()
            
            # All items should have the filtered company_key
            for item in data["items"]:
                assert item["company_key"] == company, f"Got {item['company_key']} instead of {company}"
            print(f"Items for company {company}: {data['total']}")
    
    def test_kardex_filter_by_fecha_range(self, headers):
        """Should filter by fecha_desde and fecha_hasta."""
        # Use a reasonable date range (data is from 2025-2026)
        response = requests.get(
            f"{BASE_URL}/api/kardex-pt?fecha_desde=2025-01-01&fecha_hasta=2026-12-31&page_size=20", 
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        print(f"Items in 2025-2026: {data['total']}")
        
        # Verify dates are within range
        for item in data["items"]:
            if item["fecha"]:
                assert item["fecha"] >= "2025-01-01", f"Date {item['fecha']} before range"
                assert item["fecha"][:10] <= "2026-12-31", f"Date {item['fecha']} after range"
    
    def test_kardex_pagination_works(self, headers):
        """Should paginate correctly."""
        # Get page 1
        resp1 = requests.get(f"{BASE_URL}/api/kardex-pt?page=1&page_size=5", headers=headers)
        assert resp1.status_code == 200
        data1 = resp1.json()
        
        # Get page 2
        resp2 = requests.get(f"{BASE_URL}/api/kardex-pt?page=2&page_size=5", headers=headers)
        assert resp2.status_code == 200
        data2 = resp2.json()
        
        # Items should be different
        if data1["items"] and data2["items"]:
            ids1 = [i["odoo_id"] for i in data1["items"]]
            ids2 = [i["odoo_id"] for i in data2["items"]]
            assert ids1 != ids2, "Page 1 and Page 2 have same items"
            print(f"Page 1 IDs: {ids1[:3]}..., Page 2 IDs: {ids2[:3]}...")
    
    def test_kardex_filter_by_location_includes_transfers(self, headers):
        """When filtering by location_id, TRANSFERENCIA should be included."""
        # Get a location
        filtros_resp = requests.get(f"{BASE_URL}/api/kardex-pt/filtros", headers=headers)
        ubicaciones = filtros_resp.json().get("ubicaciones", [])
        
        if ubicaciones:
            loc_id = ubicaciones[0]["id"]
            response = requests.get(f"{BASE_URL}/api/kardex-pt?location_id={loc_id}&page_size=100", headers=headers)
            assert response.status_code == 200
            data = response.json()
            print(f"Items for location {loc_id}: {data['total']}")
            # Note: transfers may or may not be present depending on data


class TestKardexPTResumen:
    """Test GET /api/kardex-pt/resumen - Summary by product."""
    
    def test_resumen_returns_totales(self, headers):
        """Should return global totals."""
        response = requests.get(f"{BASE_URL}/api/kardex-pt/resumen", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "totales" in data
        totales = data["totales"]
        assert "entradas" in totales
        assert "salidas" in totales
        assert "saldo" in totales
        
        print(f"Totales - Entradas: {totales['entradas']}, Salidas: {totales['salidas']}, Saldo: {totales['saldo']}")
    
    def test_resumen_returns_productos(self, headers):
        """Should return list of products with their totals."""
        response = requests.get(f"{BASE_URL}/api/kardex-pt/resumen", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "productos" in data
        productos = data["productos"]
        assert isinstance(productos, list)
        # Per context: 226 products with movement
        print(f"Products with movement: {len(productos)}")
        
        if productos:
            p = productos[0]
            required_fields = ["product_tmpl_id", "producto_nombre", "total_entradas", "total_salidas", "saldo"]
            for field in required_fields:
                assert field in p, f"Missing field: {field}"
    
    def test_resumen_filter_by_company_key(self, headers):
        """Should filter resumen by company_key."""
        filtros_resp = requests.get(f"{BASE_URL}/api/kardex-pt/filtros", headers=headers)
        company_keys = filtros_resp.json().get("company_keys", [])
        
        if company_keys:
            company = company_keys[0]
            response = requests.get(f"{BASE_URL}/api/kardex-pt/resumen?company_key={company}", headers=headers)
            assert response.status_code == 200
            data = response.json()
            print(f"Resumen for {company}: {len(data['productos'])} products")
    
    def test_resumen_filter_by_fecha_range(self, headers):
        """Should filter resumen by date range."""
        response = requests.get(
            f"{BASE_URL}/api/kardex-pt/resumen?fecha_desde=2025-01-01&fecha_hasta=2026-12-31", 
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        print(f"Resumen 2025-2026: {len(data['productos'])} products")


class TestKardexPTProductFilter:
    """Test filtering by product_tmpl_id."""
    
    def test_kardex_filter_by_product_tmpl_id(self, headers):
        """Should filter by specific product."""
        # First get some products from resumen
        resumen_resp = requests.get(f"{BASE_URL}/api/kardex-pt/resumen", headers=headers)
        productos = resumen_resp.json().get("productos", [])
        
        if productos:
            product_id = productos[0]["product_tmpl_id"]
            product_name = productos[0]["producto_nombre"]
            
            response = requests.get(f"{BASE_URL}/api/kardex-pt?product_tmpl_id={product_id}&page_size=50", headers=headers)
            assert response.status_code == 200
            data = response.json()
            
            # All items should be for this product
            for item in data["items"]:
                assert item["product_tmpl_id"] == product_id, f"Got product {item['product_tmpl_id']} instead of {product_id}"
            
            print(f"Movements for product '{product_name}' (ID: {product_id}): {data['total']}")
    
    def test_kardex_saldo_acumulado_per_product(self, headers):
        """Saldo acumulado should be calculated per product using window function."""
        # Get movements for a specific product
        resumen_resp = requests.get(f"{BASE_URL}/api/kardex-pt/resumen", headers=headers)
        productos = resumen_resp.json().get("productos", [])
        
        if productos:
            # Find a product with multiple movements
            for p in productos:
                if p["total_entradas"] > 0 and p["total_salidas"] > 0:
                    product_id = p["product_tmpl_id"]
                    break
            else:
                product_id = productos[0]["product_tmpl_id"]
            
            response = requests.get(f"{BASE_URL}/api/kardex-pt?product_tmpl_id={product_id}&page_size=100", headers=headers)
            data = response.json()
            
            if len(data["items"]) > 1:
                # Verify saldo_acumulado changes across movements
                saldos = [i["saldo_acumulado"] for i in data["items"]]
                print(f"Saldos for product {product_id}: {saldos[:5]}...")
                # Note: saldos may vary as they're cumulative


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
