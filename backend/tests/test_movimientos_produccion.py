"""
Test suite for MovimientosProduccion API - Server-side pagination and JOINs
Focus: Testing the refactored endpoint that eliminates N+1 queries
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestMovimientosProduccionAPI:
    """Tests for GET /api/movimientos-produccion with server-side pagination"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Login and get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "username": "eduard",
            "password": "eduard123"
        }, timeout=15)
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            if token:
                self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        yield
        self.session.close()

    def test_movimientos_pagination_basic(self):
        """Test: GET /api/movimientos-produccion?limit=5&offset=0 returns paginated response"""
        response = self.session.get(
            f"{BASE_URL}/api/movimientos-produccion",
            params={"limit": 5, "offset": 0},
            timeout=15
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify paginated response structure
        assert "items" in data, "Response should have 'items' key"
        assert "total" in data, "Response should have 'total' key"
        assert "limit" in data, "Response should have 'limit' key"
        assert "offset" in data, "Response should have 'offset' key"
        
        # Verify pagination values
        assert data["limit"] == 5
        assert data["offset"] == 0
        assert isinstance(data["total"], int)
        assert isinstance(data["items"], list)
        assert len(data["items"]) <= 5
        
        print(f"✓ Pagination works: {len(data['items'])} items returned, total: {data['total']}")

    def test_movimientos_join_fields(self):
        """Test: Response includes servicio_nombre, persona_nombre, registro_n_corte from JOINs"""
        response = self.session.get(
            f"{BASE_URL}/api/movimientos-produccion",
            params={"limit": 10, "offset": 0},
            timeout=15
        )
        
        assert response.status_code == 200
        data = response.json()
        
        if len(data["items"]) > 0:
            item = data["items"][0]
            
            # Verify JOIN fields are present (eliminates N+1 queries)
            assert "servicio_nombre" in item, "Should have servicio_nombre from JOIN"
            assert "persona_nombre" in item, "Should have persona_nombre from JOIN"
            assert "registro_n_corte" in item, "Should have registro_n_corte from JOIN"
            
            print(f"✓ JOIN fields present: servicio={item.get('servicio_nombre')}, persona={item.get('persona_nombre')}, corte={item.get('registro_n_corte')}")
        else:
            pytest.skip("No movimientos data to verify JOIN fields")

    def test_movimientos_all_true_returns_array(self):
        """Test: GET /api/movimientos-produccion?all=true returns plain array (for RegistroForm)"""
        # First get a registro_id to filter
        registros_response = self.session.get(
            f"{BASE_URL}/api/registros",
            params={"limit": 1},
            timeout=15
        )
        
        if registros_response.status_code != 200 or not registros_response.json().get("items"):
            pytest.skip("No registros available to test")
        
        registro_id = registros_response.json()["items"][0]["id"]
        
        # Test all=true with registro_id filter
        response = self.session.get(
            f"{BASE_URL}/api/movimientos-produccion",
            params={"all": "true", "registro_id": registro_id},
            timeout=15
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # When all=true, should return plain array, not paginated object
        assert isinstance(data, list), f"Expected list when all=true, got {type(data)}"
        print(f"✓ all=true returns array with {len(data)} items for registro_id={registro_id}")

    def test_movimientos_filter_by_servicio(self):
        """Test: GET /api/movimientos-produccion?servicio_id=X filters by service"""
        # First get a servicio_id
        servicios_response = self.session.get(
            f"{BASE_URL}/api/servicios-produccion",
            timeout=15
        )
        
        if servicios_response.status_code != 200 or not servicios_response.json():
            pytest.skip("No servicios available to test")
        
        servicio_id = servicios_response.json()[0]["id"]
        
        # Test filter by servicio_id
        response = self.session.get(
            f"{BASE_URL}/api/movimientos-produccion",
            params={"servicio_id": servicio_id, "limit": 50},
            timeout=15
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all returned items have the correct servicio_id
        for item in data["items"]:
            assert item["servicio_id"] == servicio_id, f"Item has wrong servicio_id: {item['servicio_id']}"
        
        print(f"✓ Filter by servicio_id works: {len(data['items'])} items for servicio={servicio_id}")

    def test_movimientos_search(self):
        """Test: GET /api/movimientos-produccion?search=X searches across corte, servicio, persona"""
        # First get some data to know what to search for
        response = self.session.get(
            f"{BASE_URL}/api/movimientos-produccion",
            params={"limit": 5},
            timeout=15
        )
        
        if response.status_code != 200 or not response.json().get("items"):
            pytest.skip("No movimientos data to test search")
        
        # Get a servicio_nombre to search for
        first_item = response.json()["items"][0]
        search_term = first_item.get("servicio_nombre", "")[:5] if first_item.get("servicio_nombre") else ""
        
        if not search_term:
            pytest.skip("No servicio_nombre to search for")
        
        # Test search
        search_response = self.session.get(
            f"{BASE_URL}/api/movimientos-produccion",
            params={"search": search_term, "limit": 50},
            timeout=15
        )
        
        assert search_response.status_code == 200
        search_data = search_response.json()
        
        # Should return results matching the search term
        assert len(search_data["items"]) > 0, f"Search for '{search_term}' should return results"
        print(f"✓ Search works: '{search_term}' returned {len(search_data['items'])} items")

    def test_movimientos_large_dataset_performance(self):
        """Test: Verify endpoint handles large dataset (3422+ records) without timeout"""
        import time
        
        start_time = time.time()
        response = self.session.get(
            f"{BASE_URL}/api/movimientos-produccion",
            params={"limit": 50, "offset": 0},
            timeout=15
        )
        elapsed = time.time() - start_time
        
        assert response.status_code == 200
        data = response.json()
        
        # Should respond quickly (under 5 seconds) even with large dataset
        assert elapsed < 5, f"Response took too long: {elapsed:.2f}s"
        
        # Verify total count is substantial (should be ~3422)
        print(f"✓ Performance OK: {elapsed:.2f}s for {data['total']} total records")

    def test_movimientos_offset_pagination(self):
        """Test: Verify offset pagination works correctly"""
        # Get first page
        page1_response = self.session.get(
            f"{BASE_URL}/api/movimientos-produccion",
            params={"limit": 5, "offset": 0},
            timeout=15
        )
        
        assert page1_response.status_code == 200
        page1_data = page1_response.json()
        
        if page1_data["total"] <= 5:
            pytest.skip("Not enough data to test pagination offset")
        
        # Get second page
        page2_response = self.session.get(
            f"{BASE_URL}/api/movimientos-produccion",
            params={"limit": 5, "offset": 5},
            timeout=15
        )
        
        assert page2_response.status_code == 200
        page2_data = page2_response.json()
        
        # Verify different items on different pages
        page1_ids = {item["id"] for item in page1_data["items"]}
        page2_ids = {item["id"] for item in page2_data["items"]}
        
        assert page1_ids.isdisjoint(page2_ids), "Page 1 and Page 2 should have different items"
        print(f"✓ Offset pagination works: page1 has {len(page1_ids)} items, page2 has {len(page2_ids)} items")


class TestModelosAPIStillWorks:
    """Verify Modelos API still works after file rewrite"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Login and get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "username": "eduard",
            "password": "eduard123"
        }, timeout=15)
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            if token:
                self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        yield
        self.session.close()

    def test_modelos_pagination_still_works(self):
        """Test: GET /api/modelos?limit=5&offset=0 still returns paginated response"""
        response = self.session.get(
            f"{BASE_URL}/api/modelos",
            params={"limit": 5, "offset": 0},
            timeout=15
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "items" in data
        assert "total" in data
        assert data["total"] > 0, "Should have modelos data"
        print(f"✓ Modelos pagination still works: {len(data['items'])} items, total: {data['total']}")

    def test_modelos_all_true_still_works(self):
        """Test: GET /api/modelos?all=true still returns plain array"""
        response = self.session.get(
            f"{BASE_URL}/api/modelos",
            params={"all": "true"},
            timeout=15
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list), f"Expected list when all=true, got {type(data)}"
        print(f"✓ Modelos all=true still works: {len(data)} items")

    def test_modelos_filtros_still_works(self):
        """Test: GET /api/modelos-filtros still returns filter options"""
        response = self.session.get(
            f"{BASE_URL}/api/modelos-filtros",
            timeout=15
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "marcas" in data
        assert "tipos" in data
        assert "entalles" in data
        assert "telas" in data
        print(f"✓ Modelos filtros still works: {len(data['marcas'])} marcas, {len(data['tipos'])} tipos")


class TestRegistroFormMovimientosIntegration:
    """Test that RegistroForm can still load movimientos correctly"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Login and get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "username": "eduard",
            "password": "eduard123"
        }, timeout=15)
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            if token:
                self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        yield
        self.session.close()

    def test_registro_form_movimientos_load(self):
        """Test: RegistroForm uses ?all=true&registro_id=X to load movimientos"""
        # Get a registro with movimientos
        registros_response = self.session.get(
            f"{BASE_URL}/api/registros",
            params={"limit": 10},
            timeout=15
        )
        
        if registros_response.status_code != 200:
            pytest.skip("Cannot get registros")
        
        registros = registros_response.json().get("items", [])
        if not registros:
            pytest.skip("No registros available")
        
        # Try to find a registro with movimientos
        for registro in registros:
            registro_id = registro["id"]
            
            # This is how RegistroForm loads movimientos
            mov_response = self.session.get(
                f"{BASE_URL}/api/movimientos-produccion",
                params={"all": "true", "registro_id": registro_id},
                timeout=15
            )
            
            assert mov_response.status_code == 200
            movimientos = mov_response.json()
            
            # Should be a list (not paginated object)
            assert isinstance(movimientos, list), "RegistroForm expects array response"
            
            if len(movimientos) > 0:
                # Verify movimientos have required fields
                mov = movimientos[0]
                assert "servicio_nombre" in mov or "servicio_id" in mov
                assert "persona_nombre" in mov or "persona_id" in mov
                print(f"✓ RegistroForm movimientos load works: {len(movimientos)} movimientos for registro {registro_id}")
                return
        
        print("✓ RegistroForm movimientos load works (no movimientos found for test registros)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
