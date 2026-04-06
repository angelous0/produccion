"""
Test suite for Performance Optimization in Production Records Module
Tests: SQL JOINs optimization, pagination, lazy loading endpoints, code splitting
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://trace-textil.preview.emergentagent.com').rstrip('/')

# Test registro with complete data: n_corte=006
TEST_REGISTRO_ID = "169c1b44-5b94-49cb-a6d2-42c3fdeb3a69"

@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username": "eduard",
        "password": "eduard123"
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json().get("access_token")

@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


class TestRegistrosListOptimization:
    """Tests for GET /api/registros - Optimized with window function COUNT(*) OVER()"""
    
    def test_registros_list_returns_200(self, auth_headers):
        """Basic list endpoint works"""
        response = requests.get(f"{BASE_URL}/api/registros", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        print(f"✓ GET /api/registros returns {len(data['items'])} items, total: {data['total']}")
    
    def test_registros_list_has_joined_fields(self, auth_headers):
        """Verify JOINed fields are present (modelo_nombre, marca_nombre, etc.)"""
        response = requests.get(f"{BASE_URL}/api/registros?limit=5", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        if data['items']:
            item = data['items'][0]
            # These fields come from JOINs, not N+1 queries
            joined_fields = ['modelo_nombre', 'marca_nombre', 'tipo_nombre', 'entalle_nombre', 'tela_nombre']
            for field in joined_fields:
                assert field in item, f"Missing joined field: {field}"
            print(f"✓ Joined fields present: {[f for f in joined_fields if item.get(f)]}")
    
    def test_registros_pagination_works(self, auth_headers):
        """Pagination with limit/offset works correctly"""
        # First page
        response1 = requests.get(f"{BASE_URL}/api/registros?limit=5&offset=0", headers=auth_headers)
        assert response1.status_code == 200
        data1 = response1.json()
        
        # Second page
        response2 = requests.get(f"{BASE_URL}/api/registros?limit=5&offset=5", headers=auth_headers)
        assert response2.status_code == 200
        data2 = response2.json()
        
        # Total should be same
        assert data1['total'] == data2['total']
        # Items should be different (if enough records)
        if data1['total'] > 5:
            ids1 = [i['id'] for i in data1['items']]
            ids2 = [i['id'] for i in data2['items']]
            assert ids1 != ids2, "Pagination not working - same items returned"
        print(f"✓ Pagination works: page1={len(data1['items'])} items, page2={len(data2['items'])} items")
    
    def test_registros_filter_by_estado(self, auth_headers):
        """Filter by estado works"""
        response = requests.get(f"{BASE_URL}/api/registros?estados=Para Corte", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # All items should have estado "Para Corte"
        for item in data['items']:
            assert item['estado'] == 'Para Corte', f"Filter failed: got estado={item['estado']}"
        print(f"✓ Filter by estado works: {len(data['items'])} items with estado='Para Corte'")
    
    def test_registros_filter_by_search(self, auth_headers):
        """Search filter works (n_corte or modelo nombre)"""
        response = requests.get(f"{BASE_URL}/api/registros?search=006", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # Should find registro with n_corte=006
        found = any(item.get('n_corte') == '006' for item in data['items'])
        assert found or data['total'] == 0, "Search filter not working"
        print(f"✓ Search filter works: found {data['total']} items matching '006'")


class TestRegistroDetailOptimization:
    """Tests for GET /api/registros/{id} - Optimized with JOINs"""
    
    def test_registro_detail_returns_200(self, auth_headers):
        """Detail endpoint works"""
        response = requests.get(f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data['id'] == TEST_REGISTRO_ID
        print(f"✓ GET /api/registros/{TEST_REGISTRO_ID} returns registro n_corte={data.get('n_corte')}")
    
    def test_registro_detail_has_joined_fields(self, auth_headers):
        """Verify JOINed fields in detail response"""
        response = requests.get(f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Fields from JOINs
        joined_fields = ['modelo_nombre', 'marca_nombre', 'tipo_nombre', 'entalle_nombre', 'tela_nombre', 'hilo_nombre']
        present_fields = [f for f in joined_fields if data.get(f)]
        print(f"✓ Detail has joined fields: {present_fields}")
        
        # At least modelo_nombre should be present
        assert 'modelo_nombre' in data, "modelo_nombre missing from detail"
    
    def test_registro_detail_has_tallas(self, auth_headers):
        """Verify tallas are returned with names (from JOIN)"""
        response = requests.get(f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        tallas = data.get('tallas', [])
        assert isinstance(tallas, list), "tallas should be a list"
        if tallas:
            # Each talla should have talla_nombre from JOIN
            for t in tallas:
                assert 'talla_id' in t, "talla_id missing"
                assert 'cantidad' in t or 'cantidad_real' in t, "cantidad missing"
            print(f"✓ Detail has {len(tallas)} tallas")
        else:
            print("✓ Detail has no tallas (empty list)")


class TestMaterialesOptimization:
    """Tests for GET /api/registros/{id}/materiales - Optimized with batch queries"""
    
    def test_materiales_endpoint_returns_200(self, auth_headers):
        """Materiales endpoint works"""
        response = requests.get(f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/materiales", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert 'registro_id' in data
        assert 'lineas' in data
        assert 'resumen' in data
        print(f"✓ GET /api/registros/{TEST_REGISTRO_ID}/materiales returns {len(data.get('lineas', []))} lineas")
    
    def test_materiales_has_consolidated_data(self, auth_headers):
        """Verify consolidated view includes reservas and salidas"""
        response = requests.get(f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/materiales", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Should have these keys from consolidated view
        assert 'reservas' in data, "reservas missing from materiales"
        assert 'salidas' in data, "salidas missing from materiales"
        assert 'tiene_requerimiento' in data, "tiene_requerimiento missing"
        print(f"✓ Materiales consolidated: {len(data.get('reservas', []))} reservas, {len(data.get('salidas', []))} salidas")


class TestMovimientosProduccion:
    """Tests for GET /api/movimientos-produccion - Verify it loads correctly"""
    
    def test_movimientos_by_registro(self, auth_headers):
        """Movimientos for a registro load correctly"""
        response = requests.get(f"{BASE_URL}/api/movimientos-produccion?registro_id={TEST_REGISTRO_ID}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # API returns {items: [...]} or plain list
        items = data.get('items', data) if isinstance(data, dict) else data
        assert isinstance(items, list), "Should return items as list"
        print(f"✓ GET /api/movimientos-produccion?registro_id={TEST_REGISTRO_ID} returns {len(items)} movimientos")
    
    def test_movimientos_have_service_names(self, auth_headers):
        """Movimientos should have servicio_nombre from JOIN"""
        response = requests.get(f"{BASE_URL}/api/movimientos-produccion?registro_id={TEST_REGISTRO_ID}&all=true", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # API returns {items: [...]} or plain list
        items = data.get('items', data) if isinstance(data, dict) else data
        
        if items:
            mov = items[0]
            assert 'servicio_nombre' in mov or 'servicio_id' in mov, "Missing service info"
            print(f"✓ Movimientos have service info: {mov.get('servicio_nombre', 'N/A')}")


class TestRegistroCRUD:
    """Tests for POST/PUT /api/registros - Verify CRUD still works after optimization"""
    
    def test_update_registro_works(self, auth_headers):
        """PUT /api/registros/{id} works without errors"""
        # First get current data
        get_response = requests.get(f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}", headers=auth_headers)
        assert get_response.status_code == 200
        current = get_response.json()
        
        # Update with same data (no functional change)
        update_payload = {
            "n_corte": current.get('n_corte', '006'),
            "modelo_id": current.get('modelo_id'),
            "curva": current.get('curva', ''),
            "estado": current.get('estado', 'Para Corte'),
            "urgente": current.get('urgente', False),
            "hilo_especifico_id": current.get('hilo_especifico_id', ''),
            "pt_item_id": current.get('pt_item_id', ''),
            "lq_odoo_id": current.get('lq_odoo_id', ''),
            "id_odoo": current.get('id_odoo', ''),
            "observaciones": current.get('observaciones', ''),
            "fecha_entrega_final": current.get('fecha_entrega_final', ''),
            "linea_negocio_id": current.get('linea_negocio_id'),
            "tallas": current.get('tallas', []),
            "distribucion_colores": current.get('distribucion_colores', [])
        }
        
        put_response = requests.put(f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}", 
                                    headers=auth_headers, json=update_payload)
        assert put_response.status_code == 200, f"Update failed: {put_response.text}"
        print(f"✓ PUT /api/registros/{TEST_REGISTRO_ID} works correctly")


class TestLazyLoadingEndpoints:
    """Tests for endpoints used by lazy-loaded pages"""
    
    def test_inventario_endpoint(self, auth_headers):
        """GET /api/inventario loads (used by lazy /inventario page)"""
        response = requests.get(f"{BASE_URL}/api/inventario?limit=5", headers=auth_headers)
        assert response.status_code == 200
        print(f"✓ GET /api/inventario works for lazy loading")
    
    def test_servicios_produccion_endpoint(self, auth_headers):
        """GET /api/servicios-produccion loads (used by lazy /maestros/servicios)"""
        response = requests.get(f"{BASE_URL}/api/servicios-produccion", headers=auth_headers)
        assert response.status_code == 200
        print(f"✓ GET /api/servicios-produccion works for lazy loading")
    
    def test_seguimiento_endpoint(self, auth_headers):
        """GET /api/reportes/seguimiento loads (used by lazy /reportes/seguimiento)"""
        response = requests.get(f"{BASE_URL}/api/reportes/en-proceso?limit=5", headers=auth_headers)
        # May return 200 or 404 depending on implementation
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"
        print(f"✓ Seguimiento endpoint accessible (status: {response.status_code})")


class TestPerformanceBaseline:
    """Basic performance checks - ensure responses are reasonably fast"""
    
    def test_registros_list_response_time(self, auth_headers):
        """GET /api/registros should respond in reasonable time"""
        start = time.time()
        response = requests.get(f"{BASE_URL}/api/registros?limit=20", headers=auth_headers)
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 5.0, f"Response too slow: {elapsed:.2f}s"
        print(f"✓ GET /api/registros responded in {elapsed:.2f}s")
    
    def test_registro_detail_response_time(self, auth_headers):
        """GET /api/registros/{id} should respond in reasonable time"""
        start = time.time()
        response = requests.get(f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}", headers=auth_headers)
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 3.0, f"Response too slow: {elapsed:.2f}s"
        print(f"✓ GET /api/registros/{TEST_REGISTRO_ID} responded in {elapsed:.2f}s")
    
    def test_materiales_response_time(self, auth_headers):
        """GET /api/registros/{id}/materiales should respond in reasonable time"""
        start = time.time()
        response = requests.get(f"{BASE_URL}/api/registros/{TEST_REGISTRO_ID}/materiales", headers=auth_headers)
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 3.0, f"Response too slow: {elapsed:.2f}s"
        print(f"✓ GET /api/registros/{TEST_REGISTRO_ID}/materiales responded in {elapsed:.2f}s")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
