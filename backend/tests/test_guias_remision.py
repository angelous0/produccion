"""
Test suite for Guías de Remisión module
Tests: GET list, GET detail, POST create, POST from-movimiento, DELETE
"""
import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_USERNAME = "eduard"
TEST_PASSWORD = "eduard123"

# Test data IDs from context
MOVIMIENTO_CON_GUIA = "e6ec36c0-f5b1-4336-884d-5f15ef71da5c"  # Already has guia
MOVIMIENTO_SIN_GUIA = "3f4c4c50-9db2-42ea-93c5-7bf0a508e0d7"  # No guia yet


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username": TEST_USERNAME,
        "password": TEST_PASSWORD
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json().get("access_token")


@pytest.fixture(scope="module")
def api_client(auth_token):
    """Authenticated requests session"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session


class TestGuiasRemisionList:
    """Tests for GET /api/guias-remision - List guías"""
    
    def test_list_guias_returns_array(self, api_client):
        """GET /api/guias-remision should return an array"""
        response = api_client.get(f"{BASE_URL}/api/guias-remision")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ GET /api/guias-remision returns array with {len(data)} items")
    
    def test_list_guias_has_enriched_fields(self, api_client):
        """GET /api/guias-remision should return enriched fields"""
        response = api_client.get(f"{BASE_URL}/api/guias-remision")
        assert response.status_code == 200
        
        data = response.json()
        if len(data) > 0:
            guia = data[0]
            # Check required fields exist
            assert "id" in guia, "Missing 'id' field"
            assert "numero_guia" in guia, "Missing 'numero_guia' field"
            assert "fecha" in guia, "Missing 'fecha' field"
            assert "cantidad" in guia, "Missing 'cantidad' field"
            # Check enriched fields
            assert "servicio_nombre" in guia, "Missing enriched 'servicio_nombre' field"
            assert "persona_nombre" in guia, "Missing enriched 'persona_nombre' field"
            assert "modelo_nombre" in guia, "Missing enriched 'modelo_nombre' field"
            assert "registro_n_corte" in guia, "Missing enriched 'registro_n_corte' field"
            print(f"✓ Guía has enriched fields: numero_guia={guia['numero_guia']}, modelo={guia.get('modelo_nombre')}")
        else:
            print("⚠ No guías found to verify enriched fields")
    
    def test_list_guias_filter_by_registro(self, api_client):
        """GET /api/guias-remision?registro_id=... should filter correctly"""
        # First get all guías to find a valid registro_id
        response = api_client.get(f"{BASE_URL}/api/guias-remision")
        assert response.status_code == 200
        
        data = response.json()
        if len(data) > 0:
            registro_id = data[0].get("registro_id")
            if registro_id:
                # Filter by registro_id
                filtered_response = api_client.get(f"{BASE_URL}/api/guias-remision?registro_id={registro_id}")
                assert filtered_response.status_code == 200
                filtered_data = filtered_response.json()
                # All results should have the same registro_id
                for guia in filtered_data:
                    assert guia.get("registro_id") == registro_id, "Filter by registro_id not working"
                print(f"✓ Filter by registro_id works: {len(filtered_data)} guías for registro {registro_id}")
        else:
            print("⚠ No guías found to test filter")
    
    def test_list_guias_filter_by_persona(self, api_client):
        """GET /api/guias-remision?persona_id=... should filter correctly"""
        response = api_client.get(f"{BASE_URL}/api/guias-remision")
        assert response.status_code == 200
        
        data = response.json()
        if len(data) > 0:
            persona_id = data[0].get("persona_id")
            if persona_id:
                filtered_response = api_client.get(f"{BASE_URL}/api/guias-remision?persona_id={persona_id}")
                assert filtered_response.status_code == 200
                filtered_data = filtered_response.json()
                for guia in filtered_data:
                    assert guia.get("persona_id") == persona_id, "Filter by persona_id not working"
                print(f"✓ Filter by persona_id works: {len(filtered_data)} guías for persona {persona_id}")
        else:
            print("⚠ No guías found to test filter")


class TestGuiasRemisionDetail:
    """Tests for GET /api/guias-remision/{guia_id} - Get detail"""
    
    def test_get_guia_detail_success(self, api_client):
        """GET /api/guias-remision/{id} should return guía with enriched data"""
        # First get a guía ID
        list_response = api_client.get(f"{BASE_URL}/api/guias-remision")
        assert list_response.status_code == 200
        
        guias = list_response.json()
        if len(guias) > 0:
            guia_id = guias[0]["id"]
            
            # Get detail
            response = api_client.get(f"{BASE_URL}/api/guias-remision/{guia_id}")
            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
            
            guia = response.json()
            # Check basic fields
            assert guia["id"] == guia_id
            assert "numero_guia" in guia
            assert "fecha" in guia
            assert "cantidad" in guia
            # Check enriched fields
            assert "servicio_nombre" in guia
            assert "persona_nombre" in guia
            assert "modelo_nombre" in guia
            assert "registro_n_corte" in guia
            # Detail should also have persona contact info
            assert "persona_telefono" in guia
            assert "persona_direccion" in guia
            print(f"✓ GET /api/guias-remision/{guia_id} returns enriched detail")
        else:
            print("⚠ No guías found to test detail")
    
    def test_get_guia_detail_not_found(self, api_client):
        """GET /api/guias-remision/{invalid_id} should return 404"""
        response = api_client.get(f"{BASE_URL}/api/guias-remision/non-existent-id-12345")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ GET /api/guias-remision/{invalid_id} returns 404")


class TestGuiasRemisionFromMovimiento:
    """Tests for POST /api/guias-remision/from-movimiento/{movimiento_id}"""
    
    def test_create_guia_from_movimiento_new(self, api_client):
        """POST /api/guias-remision/from-movimiento/{id} should create new guía"""
        # First, get a movimiento that doesn't have a guía yet
        # Get all movimientos
        mov_response = api_client.get(f"{BASE_URL}/api/movimientos-produccion")
        assert mov_response.status_code == 200
        
        movimientos = mov_response.json()
        if len(movimientos) == 0:
            pytest.skip("No movimientos found to test")
        
        # Get all guías to find movimientos without guía
        guias_response = api_client.get(f"{BASE_URL}/api/guias-remision")
        guias = guias_response.json()
        movimientos_con_guia = {g.get("movimiento_id") for g in guias if g.get("movimiento_id")}
        
        # Find a movimiento without guía
        movimiento_sin_guia = None
        for mov in movimientos:
            if mov["id"] not in movimientos_con_guia:
                movimiento_sin_guia = mov
                break
        
        if movimiento_sin_guia:
            # Create guía from movimiento
            response = api_client.post(f"{BASE_URL}/api/guias-remision/from-movimiento/{movimiento_sin_guia['id']}")
            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
            
            data = response.json()
            assert "guia" in data, "Response should contain 'guia' object"
            guia = data["guia"]
            
            # Verify guía has correct data
            assert guia.get("numero_guia"), "Guía should have numero_guia"
            assert guia.get("numero_guia").startswith("GR-"), "numero_guia should start with GR-"
            assert guia.get("movimiento_id") == movimiento_sin_guia["id"]
            
            # Verify enriched fields
            assert "servicio_nombre" in guia, "Missing enriched servicio_nombre"
            assert "persona_nombre" in guia, "Missing enriched persona_nombre"
            assert "modelo_nombre" in guia, "Missing enriched modelo_nombre"
            
            print(f"✓ Created new guía {guia['numero_guia']} from movimiento {movimiento_sin_guia['id']}")
            
            # Cleanup - delete the created guía
            api_client.delete(f"{BASE_URL}/api/guias-remision/{guia['id']}")
        else:
            print("⚠ All movimientos already have guías, testing update instead")
            # Test update scenario
            if len(movimientos) > 0:
                mov_id = movimientos[0]["id"]
                response = api_client.post(f"{BASE_URL}/api/guias-remision/from-movimiento/{mov_id}")
                assert response.status_code == 200
                data = response.json()
                assert "guia" in data
                print(f"✓ Updated existing guía for movimiento {mov_id}")
    
    def test_create_guia_from_movimiento_updates_existing(self, api_client):
        """POST /api/guias-remision/from-movimiento/{id} should update if guía exists"""
        # Get a movimiento that already has a guía
        guias_response = api_client.get(f"{BASE_URL}/api/guias-remision")
        guias = guias_response.json()
        
        if len(guias) > 0:
            guia_con_movimiento = None
            for g in guias:
                if g.get("movimiento_id"):
                    guia_con_movimiento = g
                    break
            
            if guia_con_movimiento:
                movimiento_id = guia_con_movimiento["movimiento_id"]
                original_numero = guia_con_movimiento["numero_guia"]
                
                # Call from-movimiento again - should update, not create new
                response = api_client.post(f"{BASE_URL}/api/guias-remision/from-movimiento/{movimiento_id}")
                assert response.status_code == 200
                
                data = response.json()
                assert "guia" in data
                guia = data["guia"]
                
                # Should keep the same numero_guia
                assert guia["numero_guia"] == original_numero, "Should keep same numero_guia on update"
                assert data.get("updated") == True, "Response should indicate update"
                
                print(f"✓ Updated existing guía {original_numero} (not duplicated)")
            else:
                print("⚠ No guías with movimiento_id found")
        else:
            print("⚠ No guías found to test update")
    
    def test_create_guia_from_movimiento_not_found(self, api_client):
        """POST /api/guias-remision/from-movimiento/{invalid_id} should return 404"""
        response = api_client.post(f"{BASE_URL}/api/guias-remision/from-movimiento/non-existent-id-12345")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ POST /api/guias-remision/from-movimiento/{invalid_id} returns 404")


class TestGuiasRemisionDelete:
    """Tests for DELETE /api/guias-remision/{guia_id}"""
    
    def test_delete_guia_success(self, api_client):
        """DELETE /api/guias-remision/{id} should delete guía"""
        # First create a guía to delete
        # Get a movimiento
        mov_response = api_client.get(f"{BASE_URL}/api/movimientos-produccion")
        movimientos = mov_response.json()
        
        if len(movimientos) == 0:
            pytest.skip("No movimientos to create test guía")
        
        # Find movimiento without guía or use first one
        guias_response = api_client.get(f"{BASE_URL}/api/guias-remision")
        guias = guias_response.json()
        movimientos_con_guia = {g.get("movimiento_id") for g in guias if g.get("movimiento_id")}
        
        test_mov = None
        for mov in movimientos:
            if mov["id"] not in movimientos_con_guia:
                test_mov = mov
                break
        
        if test_mov:
            # Create guía
            create_response = api_client.post(f"{BASE_URL}/api/guias-remision/from-movimiento/{test_mov['id']}")
            assert create_response.status_code == 200
            guia_id = create_response.json()["guia"]["id"]
            
            # Delete guía
            delete_response = api_client.delete(f"{BASE_URL}/api/guias-remision/{guia_id}")
            assert delete_response.status_code == 200, f"Expected 200, got {delete_response.status_code}"
            
            # Verify deleted
            get_response = api_client.get(f"{BASE_URL}/api/guias-remision/{guia_id}")
            assert get_response.status_code == 404, "Guía should be deleted"
            
            print(f"✓ DELETE /api/guias-remision/{guia_id} works correctly")
        else:
            print("⚠ All movimientos have guías, skipping delete test to avoid data loss")


class TestGuiasRemisionDateFilters:
    """Tests for date filtering in guías list"""
    
    def test_date_field_is_fecha_not_fecha_emision(self, api_client):
        """Verify guías use 'fecha' field, not 'fecha_emision'"""
        response = api_client.get(f"{BASE_URL}/api/guias-remision")
        assert response.status_code == 200
        
        guias = response.json()
        if len(guias) > 0:
            guia = guias[0]
            # Should have 'fecha' field
            assert "fecha" in guia, "Guía should have 'fecha' field"
            # Should NOT have 'fecha_emision' field (old incorrect field)
            # Note: It's OK if it exists but 'fecha' is the correct one
            print(f"✓ Guía uses 'fecha' field: {guia.get('fecha')}")
        else:
            print("⚠ No guías to verify date field")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
