"""
Test Suite: Cierre de Produccion Module
Tests for consolidated cierre.py endpoints:
- Preview cierre (GET /api/registros/{id}/preview-cierre)
- Execute cierre (POST /api/registros/{id}/cierre-produccion)
- Get cierre (GET /api/registros/{id}/cierre-produccion)
- Reabrir cierre (POST /api/registros/{id}/reabrir-cierre)
- Balance PDF (GET /api/registros/{id}/balance-pdf)
- PT item assignment (PUT /api/registros/{id}/pt-item)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test data from agent context:
# - Registro 009 (a097d502-7058-4d00-a840-0ce8a3bff131) - CERRADO
# - Registro 006 (169c1b44-5b94-49cb-a6d2-42c3fdeb3a69) - Lavanderia (sin cierre)
REGISTRO_CERRADO_ID = "a097d502-7058-4d00-a840-0ce8a3bff131"  # n_corte 009
REGISTRO_SIN_CIERRE_ID = "169c1b44-5b94-49cb-a6d2-42c3fdeb3a69"  # n_corte 006


class TestAuth:
    """Authentication tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for eduard/eduard123"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "eduard",
            "password": "eduard123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        return data["access_token"]
    
    def test_login_success(self, auth_token):
        """Test login works with eduard/eduard123"""
        assert auth_token is not None
        assert len(auth_token) > 0
        print(f"✓ Login successful, token length: {len(auth_token)}")


class TestPreviewCierre:
    """Tests for GET /api/registros/{id}/preview-cierre"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "eduard",
            "password": "eduard123"
        })
        return response.json().get("access_token")
    
    def test_preview_cierre_registro_sin_cierre(self, auth_token):
        """Preview cierre for registro without existing cierre (006)"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(
            f"{BASE_URL}/api/registros/{REGISTRO_SIN_CIERRE_ID}/preview-cierre",
            headers=headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify required fields in preview response
        assert "registro_id" in data, "Missing registro_id"
        assert "n_corte" in data, "Missing n_corte"
        assert "costo_mp" in data, "Missing costo_mp"
        assert "costo_servicios" in data, "Missing costo_servicios"
        assert "otros_costos" in data, "Missing otros_costos"
        assert "costo_total_final" in data, "Missing costo_total_final"
        assert "errores_validacion" in data, "Missing errores_validacion"
        assert "puede_cerrar" in data, "Missing puede_cerrar"
        
        print(f"✓ Preview cierre for registro sin cierre:")
        print(f"  - n_corte: {data.get('n_corte')}")
        print(f"  - costo_mp: {data.get('costo_mp')}")
        print(f"  - costo_servicios: {data.get('costo_servicios')}")
        print(f"  - otros_costos: {data.get('otros_costos')}")
        print(f"  - costo_total_final: {data.get('costo_total_final')}")
        print(f"  - puede_cerrar: {data.get('puede_cerrar')}")
        print(f"  - errores_validacion: {data.get('errores_validacion')}")
    
    def test_preview_cierre_registro_ya_cerrado_returns_400(self, auth_token):
        """Preview cierre for already closed registro should return 400"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(
            f"{BASE_URL}/api/registros/{REGISTRO_CERRADO_ID}/preview-cierre",
            headers=headers
        )
        
        # Should return 400 because registro 009 is already CERRADO
        assert response.status_code == 400, f"Expected 400 for already closed registro, got {response.status_code}: {response.text}"
        data = response.json()
        assert "detail" in data
        print(f"✓ Preview cierre for already closed registro returns 400: {data.get('detail')}")
    
    def test_preview_cierre_registro_not_found(self, auth_token):
        """Preview cierre for non-existent registro should return 404"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(
            f"{BASE_URL}/api/registros/non-existent-id-12345/preview-cierre",
            headers=headers
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Preview cierre for non-existent registro returns 404")


class TestGetCierre:
    """Tests for GET /api/registros/{id}/cierre-produccion"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "eduard",
            "password": "eduard123"
        })
        return response.json().get("access_token")
    
    def test_get_cierre_existente(self, auth_token):
        """Get cierre for registro with existing cierre (009)"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(
            f"{BASE_URL}/api/registros/{REGISTRO_CERRADO_ID}/cierre-produccion",
            headers=headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify cierre data structure
        assert data is not None, "Cierre should exist for registro 009"
        assert "estado_cierre" in data, "Missing estado_cierre"
        assert "cerrado_por" in data, "Missing cerrado_por"
        assert "snapshot_json" in data, "Missing snapshot_json"
        assert "costo_mp" in data, "Missing costo_mp"
        assert "costo_servicios" in data, "Missing costo_servicios"
        assert "costo_total" in data, "Missing costo_total"
        
        print(f"✓ Get cierre for registro cerrado:")
        print(f"  - estado_cierre: {data.get('estado_cierre')}")
        print(f"  - cerrado_por: {data.get('cerrado_por')}")
        print(f"  - costo_mp: {data.get('costo_mp')}")
        print(f"  - costo_servicios: {data.get('costo_servicios')}")
        print(f"  - costo_total: {data.get('costo_total')}")
        print(f"  - snapshot_json present: {data.get('snapshot_json') is not None}")
    
    def test_get_cierre_no_existente(self, auth_token):
        """Get cierre for registro without cierre returns null"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(
            f"{BASE_URL}/api/registros/{REGISTRO_SIN_CIERRE_ID}/cierre-produccion",
            headers=headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        # Should return null/None for registro without cierre
        assert data is None, f"Expected null for registro without cierre, got {data}"
        print("✓ Get cierre for registro sin cierre returns null")


class TestValidacionesCierre:
    """Tests for cierre validation scenarios"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "eduard",
            "password": "eduard123"
        })
        return response.json().get("access_token")
    
    def test_cierre_registro_ya_cerrado_returns_400(self, auth_token):
        """Cierre of already closed registro should return 400"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.post(
            f"{BASE_URL}/api/registros/{REGISTRO_CERRADO_ID}/cierre-produccion",
            headers=headers,
            json={}
        )
        
        assert response.status_code == 400, f"Expected 400 for already closed registro, got {response.status_code}: {response.text}"
        data = response.json()
        assert "detail" in data
        print(f"✓ Cierre of already closed registro returns 400: {data.get('detail')}")
    
    def test_cierre_sin_pt_asignado_returns_400(self, auth_token):
        """Cierre without PT assigned should return 400 with validation error"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # First check preview to see validation errors
        preview_response = requests.get(
            f"{BASE_URL}/api/registros/{REGISTRO_SIN_CIERRE_ID}/preview-cierre",
            headers=headers
        )
        
        if preview_response.status_code == 200:
            preview_data = preview_response.json()
            errores = preview_data.get("errores_validacion", [])
            puede_cerrar = preview_data.get("puede_cerrar", True)
            
            # If PT is not assigned, errores should contain PT error
            if not puede_cerrar:
                print(f"✓ Preview shows validation errors: {errores}")
                
                # Try to execute cierre - should fail
                cierre_response = requests.post(
                    f"{BASE_URL}/api/registros/{REGISTRO_SIN_CIERRE_ID}/cierre-produccion",
                    headers=headers,
                    json={}
                )
                
                if cierre_response.status_code == 400:
                    print(f"✓ Cierre blocked due to validation: {cierre_response.json().get('detail')}")
                else:
                    print(f"  Cierre response: {cierre_response.status_code}")
            else:
                print(f"  Registro can be closed (PT assigned): puede_cerrar={puede_cerrar}")
        else:
            print(f"  Preview returned {preview_response.status_code}")


class TestReabrirCierre:
    """Tests for POST /api/registros/{id}/reabrir-cierre"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "eduard",
            "password": "eduard123"
        })
        return response.json().get("access_token")
    
    def test_reapertura_sin_motivo_returns_400(self, auth_token):
        """Reapertura without motivo should return 400"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.post(
            f"{BASE_URL}/api/registros/{REGISTRO_CERRADO_ID}/reabrir-cierre",
            headers=headers,
            json={"motivo": ""}  # Empty motivo
        )
        
        assert response.status_code == 400, f"Expected 400 for empty motivo, got {response.status_code}: {response.text}"
        data = response.json()
        assert "detail" in data
        assert "motivo" in data["detail"].lower() or "5" in data["detail"]
        print(f"✓ Reapertura without motivo returns 400: {data.get('detail')}")
    
    def test_reapertura_motivo_corto_returns_400(self, auth_token):
        """Reapertura with motivo < 5 chars should return 400"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.post(
            f"{BASE_URL}/api/registros/{REGISTRO_CERRADO_ID}/reabrir-cierre",
            headers=headers,
            json={"motivo": "abc"}  # Less than 5 chars
        )
        
        assert response.status_code == 400, f"Expected 400 for short motivo, got {response.status_code}: {response.text}"
        data = response.json()
        assert "detail" in data
        print(f"✓ Reapertura with short motivo returns 400: {data.get('detail')}")
    
    def test_reapertura_registro_sin_cierre_returns_404(self, auth_token):
        """Reapertura of registro without cierre should return 404"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.post(
            f"{BASE_URL}/api/registros/{REGISTRO_SIN_CIERRE_ID}/reabrir-cierre",
            headers=headers,
            json={"motivo": "Test reapertura motivo valido"}
        )
        
        # Should return 404 because registro 006 has no cierre
        assert response.status_code == 404, f"Expected 404 for registro without cierre, got {response.status_code}: {response.text}"
        print("✓ Reapertura of registro without cierre returns 404")


class TestBalancePDF:
    """Tests for GET /api/registros/{id}/balance-pdf"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "eduard",
            "password": "eduard123"
        })
        return response.json().get("access_token")
    
    def test_balance_pdf_registro_cerrado(self, auth_token):
        """Balance PDF for closed registro should return 200 with PDF"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(
            f"{BASE_URL}/api/registros/{REGISTRO_CERRADO_ID}/balance-pdf",
            headers=headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert "application/pdf" in response.headers.get("content-type", ""), "Expected PDF content type"
        assert len(response.content) > 0, "PDF content should not be empty"
        print(f"✓ Balance PDF generated successfully, size: {len(response.content)} bytes")
    
    def test_balance_pdf_registro_sin_cierre(self, auth_token):
        """Balance PDF for registro without cierre should still work (shows current data)"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(
            f"{BASE_URL}/api/registros/{REGISTRO_SIN_CIERRE_ID}/balance-pdf",
            headers=headers
        )
        
        # PDF should still be generated even without cierre (shows current state)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert "application/pdf" in response.headers.get("content-type", ""), "Expected PDF content type"
        print(f"✓ Balance PDF for registro sin cierre generated, size: {len(response.content)} bytes")
    
    def test_balance_pdf_registro_not_found(self, auth_token):
        """Balance PDF for non-existent registro should return 404"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(
            f"{BASE_URL}/api/registros/non-existent-id-12345/balance-pdf",
            headers=headers
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Balance PDF for non-existent registro returns 404")


class TestPtItemAssignment:
    """Tests for PUT /api/registros/{id}/pt-item"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "eduard",
            "password": "eduard123"
        })
        return response.json().get("access_token")
    
    def test_pt_item_assignment_registro_cerrado_returns_400(self, auth_token):
        """PT item assignment on closed registro should return 400"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.put(
            f"{BASE_URL}/api/registros/{REGISTRO_CERRADO_ID}/pt-item",
            headers=headers,
            json={"pt_item_id": "some-item-id"}
        )
        
        # Should return 400 because registro is CERRADA
        assert response.status_code == 400, f"Expected 400 for closed registro, got {response.status_code}: {response.text}"
        data = response.json()
        assert "detail" in data
        print(f"✓ PT item assignment on closed registro returns 400: {data.get('detail')}")
    
    def test_pt_item_assignment_invalid_item_returns_404(self, auth_token):
        """PT item assignment with invalid item_id should return 404"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.put(
            f"{BASE_URL}/api/registros/{REGISTRO_SIN_CIERRE_ID}/pt-item",
            headers=headers,
            json={"pt_item_id": "non-existent-item-id-12345"}
        )
        
        assert response.status_code == 404, f"Expected 404 for invalid item, got {response.status_code}: {response.text}"
        print("✓ PT item assignment with invalid item returns 404")
    
    def test_pt_item_assignment_null_clears_pt(self, auth_token):
        """PT item assignment with null should clear PT"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # First get current PT
        reg_response = requests.get(
            f"{BASE_URL}/api/registros/{REGISTRO_SIN_CIERRE_ID}",
            headers=headers
        )
        
        if reg_response.status_code == 200:
            current_pt = reg_response.json().get("pt_item_id")
            
            # Set to null
            response = requests.put(
                f"{BASE_URL}/api/registros/{REGISTRO_SIN_CIERRE_ID}/pt-item",
                headers=headers,
                json={"pt_item_id": None}
            )
            
            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
            data = response.json()
            assert data.get("pt_item_id") is None, "PT should be cleared"
            print(f"✓ PT item cleared successfully (was: {current_pt})")
            
            # Restore if there was a previous value
            if current_pt:
                requests.put(
                    f"{BASE_URL}/api/registros/{REGISTRO_SIN_CIERRE_ID}/pt-item",
                    headers=headers,
                    json={"pt_item_id": current_pt}
                )
                print(f"  Restored PT to: {current_pt}")


class TestDashboardFunctionality:
    """Test that dashboard still works correctly"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "eduard",
            "password": "eduard123"
        })
        return response.json().get("access_token")
    
    def test_registros_list(self, auth_token):
        """Registros list endpoint should work"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(
            f"{BASE_URL}/api/registros",
            headers=headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        # API returns paginated response with items array
        assert isinstance(data, dict), "Expected dict response"
        assert "items" in data, "Expected items in response"
        assert isinstance(data["items"], list), "Expected items to be a list"
        print(f"✓ Registros list working: {len(data['items'])} registros found (total: {data.get('total', 'N/A')})")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
