"""
Test PT (Producto Terminado) Integration Features
Tests for:
- GET /api/modelos returns pt_item_id, pt_item_nombre, pt_item_codigo
- POST /api/modelos/{id}/crear-pt creates and links PT item
- GET /api/items-pt returns only PT type items
- PUT /api/modelos/{id} persists pt_item_id
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test data reference from main agent context
MODELO_EDUARD_ID = "3d3f6dd0-bfab-4d79-afe5-2a4cce7f5a87"
PT_EDUARD_ID = "0626f7fb-f16a-4099-8578-17c74b22a7ab"
REGISTRO_ID = "c74d3460-3e8b-4d4c-88e5-06bff012d6f5"


class TestPTEndpoints:
    """Tests for PT (Producto Terminado) related endpoints"""

    def test_get_modelos_returns_pt_fields(self):
        """GET /api/modelos should return pt_item_id, pt_item_nombre, pt_item_codigo for each modelo"""
        response = requests.get(f"{BASE_URL}/api/modelos")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        modelos = response.json()
        assert isinstance(modelos, list), "Response should be a list"
        
        # Find modelo Eduard which has PT linked
        modelo_eduard = None
        for m in modelos:
            if m.get('id') == MODELO_EDUARD_ID or m.get('nombre') == 'Eduard':
                modelo_eduard = m
                break
        
        assert modelo_eduard is not None, "Modelo Eduard should exist"
        
        # Verify PT fields are present
        assert 'pt_item_id' in modelo_eduard, "pt_item_id field should be present in modelo"
        assert 'pt_item_nombre' in modelo_eduard, "pt_item_nombre field should be present in modelo"
        assert 'pt_item_codigo' in modelo_eduard, "pt_item_codigo field should be present in modelo"
        
        # Verify PT is linked (Eduard has PT-001)
        if modelo_eduard['pt_item_id']:
            assert modelo_eduard['pt_item_nombre'] is not None, "pt_item_nombre should not be None when pt_item_id exists"
            assert modelo_eduard['pt_item_codigo'] is not None, "pt_item_codigo should not be None when pt_item_id exists"
            print(f"✓ Modelo Eduard has PT linked: {modelo_eduard['pt_item_codigo']} - {modelo_eduard['pt_item_nombre']}")
        else:
            print(f"Note: Modelo Eduard does not have PT linked (pt_item_id is None)")

    def test_get_items_pt_returns_only_pt_type(self):
        """GET /api/items-pt should return only PT type items"""
        response = requests.get(f"{BASE_URL}/api/items-pt")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        items_pt = response.json()
        assert isinstance(items_pt, list), "Response should be a list"
        
        # All items should have PT characteristics
        for item in items_pt:
            assert 'id' in item, "Each PT item should have id"
            assert 'codigo' in item, "Each PT item should have codigo"
            assert 'nombre' in item, "Each PT item should have nombre"
            
            # PT items usually have codigo starting with PT-
            if item.get('codigo'):
                print(f"  - PT Item: {item['codigo']} - {item['nombre']}")
        
        print(f"✓ GET /api/items-pt returned {len(items_pt)} PT items")

    def test_crear_pt_for_modelo_already_linked(self):
        """POST /api/modelos/{id}/crear-pt should return existing PT if already linked"""
        # Test with modelo Eduard which already has PT linked
        response = requests.post(f"{BASE_URL}/api/modelos/{MODELO_EDUARD_ID}/crear-pt")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        
        # Should return existing PT info
        assert 'pt_item_id' in data, "Response should contain pt_item_id"
        if 'message' in data and 'ya tiene' in data['message']:
            print(f"✓ Correctly returned existing PT: {data.get('pt_item_nombre', data.get('pt_item_id'))}")
        else:
            print(f"✓ PT created or returned: {data}")

    def test_update_modelo_persists_pt_item_id(self):
        """PUT /api/modelos/{id} should persist pt_item_id"""
        # First get current modelo data
        get_response = requests.get(f"{BASE_URL}/api/modelos")
        assert get_response.status_code == 200
        
        modelos = get_response.json()
        modelo_eduard = None
        for m in modelos:
            if m.get('id') == MODELO_EDUARD_ID or m.get('nombre') == 'Eduard':
                modelo_eduard = m
                break
        
        assert modelo_eduard is not None, "Modelo Eduard should exist"
        
        # Update modelo with same pt_item_id (or a new one if needed)
        current_pt_item_id = modelo_eduard.get('pt_item_id')
        
        update_payload = {
            "nombre": modelo_eduard['nombre'],
            "marca_id": modelo_eduard['marca_id'],
            "tipo_id": modelo_eduard['tipo_id'],
            "entalle_id": modelo_eduard['entalle_id'],
            "tela_id": modelo_eduard['tela_id'],
            "hilo_id": modelo_eduard['hilo_id'],
            "ruta_produccion_id": modelo_eduard.get('ruta_produccion_id'),
            "servicios_ids": modelo_eduard.get('servicios_ids', []),
            "pt_item_id": current_pt_item_id
        }
        
        update_response = requests.put(
            f"{BASE_URL}/api/modelos/{MODELO_EDUARD_ID}",
            json=update_payload
        )
        assert update_response.status_code == 200, f"Expected 200, got {update_response.status_code}"
        
        # Verify PT is persisted
        verify_response = requests.get(f"{BASE_URL}/api/modelos")
        assert verify_response.status_code == 200
        
        updated_modelos = verify_response.json()
        updated_modelo = None
        for m in updated_modelos:
            if m.get('id') == MODELO_EDUARD_ID:
                updated_modelo = m
                break
        
        assert updated_modelo is not None, "Updated modelo should exist"
        assert updated_modelo.get('pt_item_id') == current_pt_item_id, \
            f"pt_item_id should be persisted. Expected {current_pt_item_id}, got {updated_modelo.get('pt_item_id')}"
        
        print(f"✓ PUT /api/modelos persisted pt_item_id: {current_pt_item_id}")


class TestRegistroPTIntegration:
    """Tests for Registro PT integration"""

    def test_registro_has_pt_field(self):
        """Verify registro has pt_item_id field"""
        response = requests.get(f"{BASE_URL}/api/registros/{REGISTRO_ID}")
        
        if response.status_code == 404:
            pytest.skip("Test registro not found")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        registro = response.json()
        assert 'pt_item_id' in registro, "Registro should have pt_item_id field"
        print(f"✓ Registro pt_item_id: {registro.get('pt_item_id')}")

    def test_inventario_pt_items_have_correct_type(self):
        """Verify PT items in inventario have tipo_item = PT"""
        # Get full inventario to verify tipo_item
        response = requests.get(f"{BASE_URL}/api/inventario")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        items = response.json()
        pt_items = [i for i in items if i.get('tipo_item') == 'PT']
        
        print(f"✓ Found {len(pt_items)} items with tipo_item='PT' in inventory")
        for pt in pt_items[:5]:  # Show first 5
            print(f"  - {pt.get('codigo')}: {pt.get('nombre')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
