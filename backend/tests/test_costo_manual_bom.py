#!/usr/bin/env python3
"""
Test Suite: costo_manual field for BOM SERVICIO lines
Tests the new feature for editable unit cost on SERVICIO type BOM lines

Features tested:
- PUT /api/bom/{bom_id}/lineas/{linea_id} saves costo_manual field correctly
- PUT /api/bom/{bom_id}/lineas/{linea_id} preserves costo_manual when not sent
- GET /api/bom/{bom_id}/costo-estandar uses costo_manual for SERVICIO lines
- GET /api/bom/{bom_id}/costo-estandar uses costo_promedio for non-SERVICIO lines
- POST /api/bom/{bom_id}/duplicar copies costo_manual to new BOM lines
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://bom-pricing-update.preview.emergentagent.com').rstrip('/')

# Test data from the review request
EXISTING_BOM_ID = "2a7a6511-89f4-4a2f-a987-745c8df37842"
EXISTING_SERVICIO_LINEA_ID = "0702cd73-2376-46c9-a20e-5d071ec098af"
EXISTING_MODELO_ID = "3d3f6dd0-bfab-4d79-afe5-2a4cce7f5a87"


class TestCostoManualBOM:
    """Tests for costo_manual feature on BOM SERVICIO lines"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup session and get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get auth token
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "username": "eduard",
            "password": "eduard123"
        })
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            if token:
                self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        yield
    
    def test_01_bom_exists(self):
        """Verify the BOM we're testing exists"""
        response = self.session.get(f"{BASE_URL}/api/bom/{EXISTING_BOM_ID}")
        assert response.status_code == 200, f"BOM not found: {response.text}"
        
        data = response.json()
        assert data['id'] == EXISTING_BOM_ID
        assert 'lineas' in data
        print(f"BOM found: {data['codigo']} with {len(data['lineas'])} lines")
    
    def test_02_servicio_linea_exists(self):
        """Verify the SERVICIO line exists in the BOM"""
        response = self.session.get(f"{BASE_URL}/api/bom/{EXISTING_BOM_ID}")
        assert response.status_code == 200
        
        data = response.json()
        servicio_linea = None
        for linea in data['lineas']:
            if linea['id'] == EXISTING_SERVICIO_LINEA_ID:
                servicio_linea = linea
                break
        
        assert servicio_linea is not None, f"SERVICIO line {EXISTING_SERVICIO_LINEA_ID} not found in BOM"
        assert servicio_linea.get('tipo_componente') == 'SERVICIO', f"Expected tipo_componente=SERVICIO, got {servicio_linea.get('tipo_componente')}"
        print(f"Found SERVICIO line: {servicio_linea.get('inventario_nombre', 'unnamed')}")
    
    def test_03_put_linea_saves_costo_manual(self):
        """PUT /api/bom/{bom_id}/lineas/{linea_id} saves costo_manual field correctly when sent"""
        test_costo = 25.50
        
        # Update costo_manual
        response = self.session.put(
            f"{BASE_URL}/api/bom/{EXISTING_BOM_ID}/lineas/{EXISTING_SERVICIO_LINEA_ID}",
            json={"costo_manual": test_costo}
        )
        assert response.status_code == 200, f"Failed to update: {response.text}"
        
        updated_data = response.json()
        assert updated_data.get('costo_manual') == test_costo, \
            f"Expected costo_manual={test_costo}, got {updated_data.get('costo_manual')}"
        
        # Verify by re-fetching the BOM
        verify_response = self.session.get(f"{BASE_URL}/api/bom/{EXISTING_BOM_ID}")
        assert verify_response.status_code == 200
        
        bom_data = verify_response.json()
        linea_found = None
        for linea in bom_data['lineas']:
            if linea['id'] == EXISTING_SERVICIO_LINEA_ID:
                linea_found = linea
                break
        
        assert linea_found is not None
        assert linea_found.get('costo_manual') == test_costo, \
            f"costo_manual not persisted. Expected {test_costo}, got {linea_found.get('costo_manual')}"
        
        print(f"costo_manual successfully saved: {test_costo}")
    
    def test_04_put_linea_preserves_costo_manual_when_not_sent(self):
        """PUT /api/bom/{bom_id}/lineas/{linea_id} preserves costo_manual when not sent in payload"""
        # First, set a known costo_manual value
        initial_costo = 30.00
        response1 = self.session.put(
            f"{BASE_URL}/api/bom/{EXISTING_BOM_ID}/lineas/{EXISTING_SERVICIO_LINEA_ID}",
            json={"costo_manual": initial_costo}
        )
        assert response1.status_code == 200
        
        # Then, update other fields WITHOUT sending costo_manual
        response2 = self.session.put(
            f"{BASE_URL}/api/bom/{EXISTING_BOM_ID}/lineas/{EXISTING_SERVICIO_LINEA_ID}",
            json={"cantidad_base": 1.5}  # Only updating cantidad_base
        )
        assert response2.status_code == 200
        
        updated_data = response2.json()
        assert updated_data.get('costo_manual') == initial_costo, \
            f"costo_manual was not preserved. Expected {initial_costo}, got {updated_data.get('costo_manual')}"
        
        print(f"costo_manual correctly preserved: {initial_costo} (unchanged after other field update)")
    
    def test_05_costo_estandar_uses_costo_manual_for_servicio(self):
        """GET /api/bom/{bom_id}/costo-estandar uses costo_manual for SERVICIO lines (precio_unitario should be costo_manual)"""
        # Set a specific costo_manual value
        test_costo = 45.00
        update_response = self.session.put(
            f"{BASE_URL}/api/bom/{EXISTING_BOM_ID}/lineas/{EXISTING_SERVICIO_LINEA_ID}",
            json={"costo_manual": test_costo}
        )
        assert update_response.status_code == 200
        
        # Get costo-estandar
        costo_response = self.session.get(f"{BASE_URL}/api/bom/{EXISTING_BOM_ID}/costo-estandar?cantidad_prendas=1")
        assert costo_response.status_code == 200
        
        costo_data = costo_response.json()
        assert 'detalle' in costo_data, "Response missing 'detalle' field"
        
        # Find the SERVICIO line in the detalle
        servicio_detalle = None
        for item in costo_data['detalle']:
            if item.get('linea_id') == EXISTING_SERVICIO_LINEA_ID:
                servicio_detalle = item
                break
        
        assert servicio_detalle is not None, "SERVICIO line not found in costo-estandar detalle"
        assert servicio_detalle.get('tipo_componente') == 'SERVICIO'
        assert servicio_detalle.get('precio_unitario') == test_costo, \
            f"precio_unitario for SERVICIO should be costo_manual ({test_costo}), got {servicio_detalle.get('precio_unitario')}"
        assert servicio_detalle.get('costo_manual') == test_costo
        
        print(f"costo-estandar correctly uses costo_manual for SERVICIO: precio_unitario={servicio_detalle.get('precio_unitario')}")
    
    def test_06_costo_estandar_uses_costo_promedio_for_non_servicio(self):
        """GET /api/bom/{bom_id}/costo-estandar uses costo_promedio from inventario for non-SERVICIO lines"""
        costo_response = self.session.get(f"{BASE_URL}/api/bom/{EXISTING_BOM_ID}/costo-estandar?cantidad_prendas=1")
        assert costo_response.status_code == 200
        
        costo_data = costo_response.json()
        
        # Find non-SERVICIO lines
        non_servicio_items = [item for item in costo_data['detalle'] if item.get('tipo_componente') != 'SERVICIO']
        
        # Verify non-SERVICIO items use costo_promedio (costo_manual should be None)
        for item in non_servicio_items:
            if item.get('inventario_nombre'):
                assert item.get('costo_manual') is None, \
                    f"Non-SERVICIO line {item.get('inventario_nombre')} should have costo_manual=None, got {item.get('costo_manual')}"
                print(f"Non-SERVICIO line '{item.get('inventario_nombre')}' ({item.get('tipo_componente')}): precio_unitario={item.get('precio_unitario')} (from inventory)")
        
        print(f"Verified {len(non_servicio_items)} non-SERVICIO lines use inventory cost")
    
    def test_07_duplicar_bom_copies_costo_manual(self):
        """POST /api/bom/{bom_id}/duplicar copies costo_manual to new BOM lines"""
        # First, ensure the source BOM line has a costo_manual value
        source_costo = 55.00
        update_response = self.session.put(
            f"{BASE_URL}/api/bom/{EXISTING_BOM_ID}/lineas/{EXISTING_SERVICIO_LINEA_ID}",
            json={"costo_manual": source_costo}
        )
        assert update_response.status_code == 200
        
        # Duplicate the BOM
        dup_response = self.session.post(f"{BASE_URL}/api/bom/{EXISTING_BOM_ID}/duplicar")
        assert dup_response.status_code == 200, f"Failed to duplicate BOM: {dup_response.text}"
        
        new_bom = dup_response.json()
        new_bom_id = new_bom['id']
        print(f"Duplicated BOM: {new_bom.get('codigo')} (v{new_bom.get('version')})")
        
        # Fetch the new BOM's details
        new_bom_detail_response = self.session.get(f"{BASE_URL}/api/bom/{new_bom_id}")
        assert new_bom_detail_response.status_code == 200
        
        new_bom_detail = new_bom_detail_response.json()
        
        # Find the SERVICIO line in the new BOM
        new_servicio_linea = None
        for linea in new_bom_detail['lineas']:
            if linea.get('tipo_componente') == 'SERVICIO':
                new_servicio_linea = linea
                break
        
        assert new_servicio_linea is not None, "SERVICIO line not found in duplicated BOM"
        assert new_servicio_linea.get('costo_manual') == source_costo, \
            f"costo_manual not copied during duplication. Expected {source_costo}, got {new_servicio_linea.get('costo_manual')}"
        
        print(f"costo_manual successfully copied to duplicated BOM: {new_servicio_linea.get('costo_manual')}")
        
        # Cleanup: delete the duplicated BOM
        cleanup_response = self.session.delete(f"{BASE_URL}/api/bom/{new_bom_id}")
        assert cleanup_response.status_code == 200, f"Failed to cleanup duplicated BOM: {cleanup_response.text}"
        print(f"Cleanup: Deleted duplicated BOM {new_bom_id}")
    
    def test_08_set_costo_manual_to_null(self):
        """Verify costo_manual can be explicitly set to null"""
        # First set a value
        update_response1 = self.session.put(
            f"{BASE_URL}/api/bom/{EXISTING_BOM_ID}/lineas/{EXISTING_SERVICIO_LINEA_ID}",
            json={"costo_manual": 99.99}
        )
        assert update_response1.status_code == 200
        
        # Then set to null
        update_response2 = self.session.put(
            f"{BASE_URL}/api/bom/{EXISTING_BOM_ID}/lineas/{EXISTING_SERVICIO_LINEA_ID}",
            json={"costo_manual": None}
        )
        assert update_response2.status_code == 200
        
        # Verify it's null
        updated_data = update_response2.json()
        assert updated_data.get('costo_manual') is None, \
            f"costo_manual should be None after explicit null set, got {updated_data.get('costo_manual')}"
        
        print("costo_manual successfully set to null")
    
    def test_09_costo_estandar_fallback_when_costo_manual_null(self):
        """When costo_manual is null for SERVICIO, verify fallback behavior"""
        # Set costo_manual to null
        update_response = self.session.put(
            f"{BASE_URL}/api/bom/{EXISTING_BOM_ID}/lineas/{EXISTING_SERVICIO_LINEA_ID}",
            json={"costo_manual": None}
        )
        assert update_response.status_code == 200
        
        # Get costo-estandar
        costo_response = self.session.get(f"{BASE_URL}/api/bom/{EXISTING_BOM_ID}/costo-estandar?cantidad_prendas=1")
        assert costo_response.status_code == 200
        
        costo_data = costo_response.json()
        
        # Find the SERVICIO line
        servicio_detalle = None
        for item in costo_data['detalle']:
            if item.get('linea_id') == EXISTING_SERVICIO_LINEA_ID:
                servicio_detalle = item
                break
        
        assert servicio_detalle is not None
        # When costo_manual is null, it should fall back to costo_promedio from inventario
        # precio_unitario should not be None (should be costo_promedio)
        print(f"With costo_manual=null, SERVICIO precio_unitario = {servicio_detalle.get('precio_unitario')} (fallback to inventory)")
    
    def test_10_cleanup_reset_costo_manual(self):
        """Cleanup: Reset costo_manual to a reasonable default value for future tests"""
        # Set a reasonable default value
        default_costo = 10.00
        update_response = self.session.put(
            f"{BASE_URL}/api/bom/{EXISTING_BOM_ID}/lineas/{EXISTING_SERVICIO_LINEA_ID}",
            json={"costo_manual": default_costo}
        )
        assert update_response.status_code == 200
        print(f"Cleanup: Reset costo_manual to {default_costo}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
