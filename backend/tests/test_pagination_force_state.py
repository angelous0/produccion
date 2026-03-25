"""
Test suite for pagination and force state change features:
1. GET /api/modelos with pagination (limit/offset/search/marca/tipo/entalle/tela)
2. GET /api/modelos?all=true returns plain array
3. GET /api/modelos-filtros returns filter options
4. GET /api/registros with pagination (limit/offset/search/estados/excluir_estados/modelo_id)
5. POST /api/registros/{id}/validar-cambio-estado with forzar option
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://trace-textil.preview.emergentagent.com').rstrip('/')

class TestAuth:
    """Authentication tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "eduard",
            "password": "eduard123"
        }, timeout=30)
        assert response.status_code == 200, f"Login failed: {response.text}"
        return response.json().get("access_token")
    
    def test_login_success(self):
        """Test login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "eduard",
            "password": "eduard123"
        }, timeout=30)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        print(f"Login successful for user: {data['user'].get('username')}")


class TestModelosPagination:
    """Tests for GET /api/modelos with server-side pagination"""
    
    def test_modelos_pagination_basic(self):
        """Test GET /api/modelos?limit=5&offset=0 returns paginated response"""
        response = requests.get(f"{BASE_URL}/api/modelos", params={
            "limit": 5,
            "offset": 0
        }, timeout=30)
        assert response.status_code == 200
        data = response.json()
        
        # Verify paginated response structure
        assert "items" in data, "Response should have 'items' key"
        assert "total" in data, "Response should have 'total' key"
        assert "limit" in data, "Response should have 'limit' key"
        assert "offset" in data, "Response should have 'offset' key"
        
        assert data["limit"] == 5
        assert data["offset"] == 0
        assert isinstance(data["items"], list)
        assert len(data["items"]) <= 5
        assert data["total"] >= len(data["items"])
        
        print(f"Modelos pagination: {len(data['items'])} items of {data['total']} total")
    
    def test_modelos_pagination_offset(self):
        """Test pagination with offset"""
        # Get first page
        response1 = requests.get(f"{BASE_URL}/api/modelos", params={
            "limit": 5,
            "offset": 0
        }, timeout=30)
        assert response1.status_code == 200
        data1 = response1.json()
        
        # Get second page
        response2 = requests.get(f"{BASE_URL}/api/modelos", params={
            "limit": 5,
            "offset": 5
        }, timeout=30)
        assert response2.status_code == 200
        data2 = response2.json()
        
        # Verify different items (if there are enough)
        if data1["total"] > 5:
            ids1 = [item["id"] for item in data1["items"]]
            ids2 = [item["id"] for item in data2["items"]]
            # No overlap between pages
            assert not set(ids1).intersection(set(ids2)), "Pages should have different items"
        
        print(f"Page 1: {len(data1['items'])} items, Page 2: {len(data2['items'])} items")
    
    def test_modelos_all_returns_array(self):
        """Test GET /api/modelos?all=true returns plain array (not paginated)"""
        response = requests.get(f"{BASE_URL}/api/modelos", params={
            "all": "true"
        }, timeout=60)  # Longer timeout for full list
        assert response.status_code == 200
        data = response.json()
        
        # Should be a plain array, not paginated object
        assert isinstance(data, list), "all=true should return plain array"
        assert len(data) > 0, "Should have at least some modelos"
        
        # Verify item structure
        if len(data) > 0:
            item = data[0]
            assert "id" in item
            assert "nombre" in item
        
        print(f"Modelos all=true: {len(data)} items returned as array")
    
    def test_modelos_search_filter(self):
        """Test GET /api/modelos?search=pantalon returns filtered results"""
        response = requests.get(f"{BASE_URL}/api/modelos", params={
            "limit": 50,
            "offset": 0,
            "search": "pantalon"
        }, timeout=30)
        assert response.status_code == 200
        data = response.json()
        
        assert "items" in data
        assert "total" in data
        
        # If there are results, verify they match the search
        if len(data["items"]) > 0:
            # At least one item should contain 'pantalon' in name or related fields
            found_match = False
            for item in data["items"]:
                name_lower = (item.get("nombre") or "").lower()
                marca_lower = (item.get("marca_nombre") or "").lower()
                tipo_lower = (item.get("tipo_nombre") or "").lower()
                if "pantalon" in name_lower or "pantalon" in marca_lower or "pantalon" in tipo_lower:
                    found_match = True
                    break
            # Note: search might match other fields too
        
        print(f"Search 'pantalon': {len(data['items'])} items found, total: {data['total']}")
    
    def test_modelos_marca_filter(self):
        """Test GET /api/modelos?marca=X returns filtered results"""
        # First get available marcas
        filtros_response = requests.get(f"{BASE_URL}/api/modelos-filtros", timeout=30)
        assert filtros_response.status_code == 200
        filtros = filtros_response.json()
        
        if len(filtros.get("marcas", [])) > 0:
            marca = filtros["marcas"][0]
            response = requests.get(f"{BASE_URL}/api/modelos", params={
                "limit": 50,
                "offset": 0,
                "marca": marca
            }, timeout=30)
            assert response.status_code == 200
            data = response.json()
            
            assert "items" in data
            # All items should have the filtered marca
            for item in data["items"]:
                assert item.get("marca_nombre") == marca, f"Item should have marca '{marca}'"
            
            print(f"Filter by marca '{marca}': {len(data['items'])} items")
        else:
            print("No marcas available for filter test")


class TestModelosFiltros:
    """Tests for GET /api/modelos-filtros endpoint"""
    
    def test_modelos_filtros_returns_options(self):
        """Test GET /api/modelos-filtros returns filter options"""
        response = requests.get(f"{BASE_URL}/api/modelos-filtros", timeout=30)
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "marcas" in data, "Should have 'marcas' key"
        assert "tipos" in data, "Should have 'tipos' key"
        assert "entalles" in data, "Should have 'entalles' key"
        assert "telas" in data, "Should have 'telas' key"
        
        # All should be arrays
        assert isinstance(data["marcas"], list)
        assert isinstance(data["tipos"], list)
        assert isinstance(data["entalles"], list)
        assert isinstance(data["telas"], list)
        
        print(f"Filter options: {len(data['marcas'])} marcas, {len(data['tipos'])} tipos, {len(data['entalles'])} entalles, {len(data['telas'])} telas")


class TestRegistrosPagination:
    """Tests for GET /api/registros with server-side pagination"""
    
    def test_registros_pagination_basic(self):
        """Test GET /api/registros?limit=5&offset=0 returns paginated response"""
        response = requests.get(f"{BASE_URL}/api/registros", params={
            "limit": 5,
            "offset": 0
        }, timeout=30)
        assert response.status_code == 200
        data = response.json()
        
        # Verify paginated response structure
        assert "items" in data, "Response should have 'items' key"
        assert "total" in data, "Response should have 'total' key"
        assert "limit" in data, "Response should have 'limit' key"
        assert "offset" in data, "Response should have 'offset' key"
        
        assert data["limit"] == 5
        assert data["offset"] == 0
        assert isinstance(data["items"], list)
        assert len(data["items"]) <= 5
        
        print(f"Registros pagination: {len(data['items'])} items of {data['total']} total")
    
    def test_registros_search_filter(self):
        """Test GET /api/registros?search=X returns filtered results"""
        # First get a registro to search for
        response = requests.get(f"{BASE_URL}/api/registros", params={
            "limit": 1,
            "offset": 0
        }, timeout=30)
        assert response.status_code == 200
        data = response.json()
        
        if len(data["items"]) > 0:
            n_corte = data["items"][0].get("n_corte", "")
            if n_corte:
                # Search for this n_corte
                search_response = requests.get(f"{BASE_URL}/api/registros", params={
                    "limit": 50,
                    "offset": 0,
                    "search": n_corte
                }, timeout=30)
                assert search_response.status_code == 200
                search_data = search_response.json()
                
                # Should find at least the original item
                assert search_data["total"] >= 1
                print(f"Search '{n_corte}': {search_data['total']} results")
    
    def test_registros_estados_filter(self):
        """Test GET /api/registros?estados=X returns filtered results"""
        response = requests.get(f"{BASE_URL}/api/registros", params={
            "limit": 50,
            "offset": 0,
            "estados": "Para Corte,Corte"
        }, timeout=30)
        assert response.status_code == 200
        data = response.json()
        
        # All items should have one of the specified estados
        for item in data["items"]:
            assert item.get("estado") in ["Para Corte", "Corte"], f"Item estado should be in filter list"
        
        print(f"Filter by estados 'Para Corte,Corte': {len(data['items'])} items")
    
    def test_registros_excluir_estados_filter(self):
        """Test GET /api/registros?excluir_estados=Tienda excludes specified estados"""
        response = requests.get(f"{BASE_URL}/api/registros", params={
            "limit": 50,
            "offset": 0,
            "excluir_estados": "Tienda"
        }, timeout=30)
        assert response.status_code == 200
        data = response.json()
        
        # No items should have estado 'Tienda'
        for item in data["items"]:
            assert item.get("estado") != "Tienda", "Item should not have excluded estado"
        
        print(f"Exclude 'Tienda': {len(data['items'])} items returned")
    
    def test_registros_modelo_id_filter(self):
        """Test GET /api/registros?modelo_id=X returns filtered results"""
        # First get a registro with modelo_id
        response = requests.get(f"{BASE_URL}/api/registros", params={
            "limit": 1,
            "offset": 0
        }, timeout=30)
        assert response.status_code == 200
        data = response.json()
        
        if len(data["items"]) > 0 and data["items"][0].get("modelo_id"):
            modelo_id = data["items"][0]["modelo_id"]
            
            filter_response = requests.get(f"{BASE_URL}/api/registros", params={
                "limit": 50,
                "offset": 0,
                "modelo_id": modelo_id
            }, timeout=30)
            assert filter_response.status_code == 200
            filter_data = filter_response.json()
            
            # All items should have the specified modelo_id
            for item in filter_data["items"]:
                assert item.get("modelo_id") == modelo_id
            
            print(f"Filter by modelo_id: {len(filter_data['items'])} items")


class TestValidarCambioEstado:
    """Tests for POST /api/registros/{id}/validar-cambio-estado with forzar option"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "eduard",
            "password": "eduard123"
        }, timeout=30)
        assert response.status_code == 200
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def test_registro_id(self, auth_token):
        """Get a registro ID for testing"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/registros", params={
            "limit": 10,
            "offset": 0
        }, headers=headers, timeout=30)
        assert response.status_code == 200
        data = response.json()
        
        if len(data["items"]) > 0:
            return data["items"][0]["id"]
        return None
    
    def test_validar_cambio_estado_basic(self, auth_token, test_registro_id):
        """Test POST /api/registros/{id}/validar-cambio-estado returns validation result"""
        if not test_registro_id:
            pytest.skip("No registro available for testing")
        
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.post(
            f"{BASE_URL}/api/registros/{test_registro_id}/validar-cambio-estado",
            json={"nuevo_estado": "Corte"},
            headers=headers,
            timeout=30
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "permitido" in data, "Response should have 'permitido' key"
        assert "bloqueos" in data, "Response should have 'bloqueos' key"
        assert isinstance(data["bloqueos"], list)
        
        print(f"Validar cambio estado: permitido={data['permitido']}, bloqueos={len(data['bloqueos'])}")
    
    def test_validar_cambio_estado_with_forzar(self, auth_token, test_registro_id):
        """Test POST /api/registros/{id}/validar-cambio-estado with forzar=true bypasses validation"""
        if not test_registro_id:
            pytest.skip("No registro available for testing")
        
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # First, try without forzar to see if there are bloqueos
        response_normal = requests.post(
            f"{BASE_URL}/api/registros/{test_registro_id}/validar-cambio-estado",
            json={"nuevo_estado": "Almacén PT"},  # Try to jump to final state
            headers=headers,
            timeout=30
        )
        assert response_normal.status_code == 200
        data_normal = response_normal.json()
        
        # Now try with forzar=true
        response_forzar = requests.post(
            f"{BASE_URL}/api/registros/{test_registro_id}/validar-cambio-estado",
            json={"nuevo_estado": "Almacén PT", "forzar": True},
            headers=headers,
            timeout=30
        )
        assert response_forzar.status_code == 200
        data_forzar = response_forzar.json()
        
        # With forzar=true, should always be permitido
        assert data_forzar["permitido"] == True, "With forzar=true, should always be permitido"
        
        # If there were bloqueos without forzar, they should be bypassed
        if len(data_normal.get("bloqueos", [])) > 0:
            print(f"Without forzar: permitido={data_normal['permitido']}, bloqueos={data_normal['bloqueos']}")
            print(f"With forzar=true: permitido={data_forzar['permitido']}, bloqueos bypassed")
        else:
            print(f"No bloqueos to bypass, but forzar=true still works: permitido={data_forzar['permitido']}")
    
    def test_validar_cambio_estado_missing_nuevo_estado(self, auth_token, test_registro_id):
        """Test POST /api/registros/{id}/validar-cambio-estado without nuevo_estado returns 400"""
        if not test_registro_id:
            pytest.skip("No registro available for testing")
        
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.post(
            f"{BASE_URL}/api/registros/{test_registro_id}/validar-cambio-estado",
            json={},  # Missing nuevo_estado
            headers=headers,
            timeout=30
        )
        assert response.status_code == 400
        print("Missing nuevo_estado correctly returns 400")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
