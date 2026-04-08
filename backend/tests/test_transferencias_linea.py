"""
Test suite for Transferencias Linea (Internal Transfers between Business Lines)
Tests CRUD operations, FIFO cost estimation, confirmation, and cancellation flows.
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://kardex-pt-sync.preview.emergentagent.com')

# Test data from context
TEST_ITEM_ID = "d402f7c9-9c4c-4a05-8f43-7589288828b0"  # Cierre YKK #5 Metal
TEST_LINEA_ORIGEN = 26  # Pantalon denim
TEST_LINEA_DESTINO = 27  # Polo


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for API calls"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": "eduard", "password": "eduard123"}
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    data = response.json()
    return data.get("access_token")


@pytest.fixture(scope="module")
def headers(auth_token):
    """Headers with auth token"""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


class TestTransferenciasLineaList:
    """Tests for GET /api/transferencias-linea - List transfers with filters"""
    
    def test_list_transferencias_success(self, headers):
        """List all transfers returns paginated response"""
        response = requests.get(
            f"{BASE_URL}/api/transferencias-linea",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert isinstance(data["items"], list)
        print(f"Found {data['total']} transferencias")
    
    def test_list_transferencias_filter_estado_borrador(self, headers):
        """Filter transfers by estado BORRADOR"""
        response = requests.get(
            f"{BASE_URL}/api/transferencias-linea?estado=BORRADOR",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["estado"] == "BORRADOR"
        print(f"Found {len(data['items'])} BORRADOR transfers")
    
    def test_list_transferencias_filter_estado_confirmado(self, headers):
        """Filter transfers by estado CONFIRMADO"""
        response = requests.get(
            f"{BASE_URL}/api/transferencias-linea?estado=CONFIRMADO",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["estado"] == "CONFIRMADO"
        print(f"Found {len(data['items'])} CONFIRMADO transfers")
    
    def test_list_transferencias_pagination(self, headers):
        """Test pagination with limit and offset"""
        response = requests.get(
            f"{BASE_URL}/api/transferencias-linea?limit=5&offset=0",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 5
        assert data["offset"] == 0
        assert len(data["items"]) <= 5


class TestStockPorLinea:
    """Tests for GET /api/transferencias-linea/stock-por-linea/{item_id}"""
    
    def test_stock_por_linea_success(self, headers):
        """Get stock breakdown by business line for an item"""
        response = requests.get(
            f"{BASE_URL}/api/transferencias-linea/stock-por-linea/{TEST_ITEM_ID}",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "item_id" in data
        assert "item_nombre" in data
        assert "item_codigo" in data
        assert "lineas" in data
        assert isinstance(data["lineas"], list)
        
        # Verify linea structure
        if data["lineas"]:
            linea = data["lineas"][0]
            assert "linea_negocio_id" in linea
            assert "linea_nombre" in linea
            assert "stock_bruto" in linea
            assert "reservado" in linea
            assert "stock_disponible" in linea
            assert "valorizado" in linea
            assert "capas_fifo" in linea
        
        print(f"Item: {data['item_nombre']}, Lineas with stock: {len(data['lineas'])}")
        for l in data["lineas"]:
            print(f"  - {l['linea_nombre']}: disponible={l['stock_disponible']}, reservado={l['reservado']}")
    
    def test_stock_por_linea_item_not_found(self, headers):
        """Returns 404 for non-existent item"""
        fake_id = str(uuid.uuid4())
        response = requests.get(
            f"{BASE_URL}/api/transferencias-linea/stock-por-linea/{fake_id}",
            headers=headers
        )
        assert response.status_code == 404
        assert "no encontrado" in response.json()["detail"].lower()


class TestEstimarCosto:
    """Tests for GET /api/transferencias-linea/estimar-costo"""
    
    def test_estimar_costo_success(self, headers):
        """Estimate FIFO cost for a transfer"""
        # First get available stock
        stock_resp = requests.get(
            f"{BASE_URL}/api/transferencias-linea/stock-por-linea/{TEST_ITEM_ID}",
            headers=headers
        )
        stock_data = stock_resp.json()
        
        # Find a linea with stock
        linea_con_stock = None
        for l in stock_data.get("lineas", []):
            if l["stock_disponible"] > 0:
                linea_con_stock = l
                break
        
        if not linea_con_stock:
            pytest.skip("No stock available for testing")
        
        cantidad_test = min(5, linea_con_stock["stock_disponible"])
        
        response = requests.get(
            f"{BASE_URL}/api/transferencias-linea/estimar-costo",
            params={
                "item_id": TEST_ITEM_ID,
                "linea_origen_id": linea_con_stock["linea_negocio_id"],
                "cantidad": cantidad_test
            },
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "capas" in data
        assert "cantidad_solicitada" in data
        assert "cantidad_cubierta" in data
        assert "costo_total_estimado" in data
        assert "stock_suficiente" in data
        assert "stock_disponible_linea" in data
        
        # Verify capas structure
        if data["capas"]:
            capa = data["capas"][0]
            assert "ingreso_id" in capa
            assert "cantidad_disponible" in capa
            assert "cantidad_a_consumir" in capa
            assert "costo_unitario" in capa
            assert "costo_parcial" in capa
        
        print(f"Estimacion: cantidad={cantidad_test}, costo_total={data['costo_total_estimado']}, capas={len(data['capas'])}")
    
    def test_estimar_costo_item_not_found(self, headers):
        """Returns 404 for non-existent item"""
        fake_id = str(uuid.uuid4())
        response = requests.get(
            f"{BASE_URL}/api/transferencias-linea/estimar-costo",
            params={
                "item_id": fake_id,
                "linea_origen_id": TEST_LINEA_ORIGEN,
                "cantidad": 10
            },
            headers=headers
        )
        assert response.status_code == 404


class TestCrearTransferencia:
    """Tests for POST /api/transferencias-linea - Create draft transfer"""
    
    def test_crear_borrador_success(self, headers):
        """Create a draft transfer successfully"""
        # First get available stock
        stock_resp = requests.get(
            f"{BASE_URL}/api/transferencias-linea/stock-por-linea/{TEST_ITEM_ID}",
            headers=headers
        )
        stock_data = stock_resp.json()
        
        # Find a linea with stock
        linea_con_stock = None
        for l in stock_data.get("lineas", []):
            if l["stock_disponible"] > 0:
                linea_con_stock = l
                break
        
        if not linea_con_stock:
            pytest.skip("No stock available for testing")
        
        # Find a different linea for destino
        linea_destino_id = TEST_LINEA_DESTINO
        if linea_destino_id == linea_con_stock["linea_negocio_id"]:
            linea_destino_id = 28  # Pantalon Qepo
        
        cantidad_test = min(1, linea_con_stock["stock_disponible"])
        
        response = requests.post(
            f"{BASE_URL}/api/transferencias-linea",
            json={
                "item_id": TEST_ITEM_ID,
                "linea_origen_id": linea_con_stock["linea_negocio_id"],
                "linea_destino_id": linea_destino_id,
                "cantidad": cantidad_test,
                "motivo": "TEST - Prueba automatizada",
                "observaciones": "Creado por test_transferencias_linea.py"
            },
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "id" in data
        assert "codigo" in data
        assert data["estado"] == "BORRADOR"
        assert "estimacion_costo" in data
        
        print(f"Created draft: {data['codigo']}, id={data['id']}")
        
        # Store for cleanup/further tests
        return data
    
    def test_crear_borrador_linea_igual_error(self, headers):
        """Returns 400 when linea_origen == linea_destino"""
        response = requests.post(
            f"{BASE_URL}/api/transferencias-linea",
            json={
                "item_id": TEST_ITEM_ID,
                "linea_origen_id": TEST_LINEA_ORIGEN,
                "linea_destino_id": TEST_LINEA_ORIGEN,  # Same as origen
                "cantidad": 1,
                "motivo": "TEST"
            },
            headers=headers
        )
        assert response.status_code == 400
        assert "misma" in response.json()["detail"].lower()
    
    def test_crear_borrador_item_not_found(self, headers):
        """Returns 404 for non-existent item"""
        fake_id = str(uuid.uuid4())
        response = requests.post(
            f"{BASE_URL}/api/transferencias-linea",
            json={
                "item_id": fake_id,
                "linea_origen_id": TEST_LINEA_ORIGEN,
                "linea_destino_id": TEST_LINEA_DESTINO,
                "cantidad": 1,
                "motivo": "TEST"
            },
            headers=headers
        )
        assert response.status_code == 404
        assert "item" in response.json()["detail"].lower()
    
    def test_crear_borrador_cantidad_cero_error(self, headers):
        """Returns 400 when cantidad <= 0"""
        response = requests.post(
            f"{BASE_URL}/api/transferencias-linea",
            json={
                "item_id": TEST_ITEM_ID,
                "linea_origen_id": TEST_LINEA_ORIGEN,
                "linea_destino_id": TEST_LINEA_DESTINO,
                "cantidad": 0,
                "motivo": "TEST"
            },
            headers=headers
        )
        assert response.status_code == 400
        assert "cantidad" in response.json()["detail"].lower() or "mayor" in response.json()["detail"].lower()
    
    def test_crear_borrador_stock_insuficiente(self, headers):
        """Returns 400 when cantidad > stock disponible"""
        response = requests.post(
            f"{BASE_URL}/api/transferencias-linea",
            json={
                "item_id": TEST_ITEM_ID,
                "linea_origen_id": TEST_LINEA_ORIGEN,
                "linea_destino_id": TEST_LINEA_DESTINO,
                "cantidad": 999999,  # Very large amount
                "motivo": "TEST"
            },
            headers=headers
        )
        assert response.status_code == 400
        assert "insuficiente" in response.json()["detail"].lower()


class TestDetalleTransferencia:
    """Tests for GET /api/transferencias-linea/{id} - Get transfer detail"""
    
    def test_detalle_transferencia_success(self, headers):
        """Get detail of an existing transfer"""
        # First list to get an existing transfer
        list_resp = requests.get(
            f"{BASE_URL}/api/transferencias-linea?limit=1",
            headers=headers
        )
        list_data = list_resp.json()
        
        if not list_data["items"]:
            pytest.skip("No transfers available for testing")
        
        transfer_id = list_data["items"][0]["id"]
        
        response = requests.get(
            f"{BASE_URL}/api/transferencias-linea/{transfer_id}",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "id" in data
        assert "codigo" in data
        assert "item_id" in data
        assert "item_nombre" in data
        assert "linea_origen_id" in data
        assert "linea_origen_nombre" in data
        assert "linea_destino_id" in data
        assert "linea_destino_nombre" in data
        assert "cantidad" in data
        assert "estado" in data
        assert "detalles" in data  # FIFO traceability
        
        print(f"Detail: {data['codigo']}, estado={data['estado']}, detalles={len(data['detalles'])}")
    
    def test_detalle_transferencia_not_found(self, headers):
        """Returns 404 for non-existent transfer"""
        fake_id = str(uuid.uuid4())
        response = requests.get(
            f"{BASE_URL}/api/transferencias-linea/{fake_id}",
            headers=headers
        )
        assert response.status_code == 404


class TestConfirmarTransferencia:
    """Tests for POST /api/transferencias-linea/{id}/confirmar"""
    
    def test_confirmar_transferencia_success(self, headers):
        """Confirm a draft transfer - full FIFO flow"""
        # First get available stock
        stock_resp = requests.get(
            f"{BASE_URL}/api/transferencias-linea/stock-por-linea/{TEST_ITEM_ID}",
            headers=headers
        )
        stock_data = stock_resp.json()
        
        # Find a linea with stock
        linea_con_stock = None
        for l in stock_data.get("lineas", []):
            if l["stock_disponible"] > 0.5:  # Need at least 0.5 for test
                linea_con_stock = l
                break
        
        if not linea_con_stock:
            pytest.skip("No stock available for testing confirmation")
        
        # Find a different linea for destino
        linea_destino_id = TEST_LINEA_DESTINO
        if linea_destino_id == linea_con_stock["linea_negocio_id"]:
            linea_destino_id = 28  # Pantalon Qepo
        
        cantidad_test = min(0.5, linea_con_stock["stock_disponible"])
        
        # Create draft
        create_resp = requests.post(
            f"{BASE_URL}/api/transferencias-linea",
            json={
                "item_id": TEST_ITEM_ID,
                "linea_origen_id": linea_con_stock["linea_negocio_id"],
                "linea_destino_id": linea_destino_id,
                "cantidad": cantidad_test,
                "motivo": "TEST - Para confirmar",
                "observaciones": "Test de confirmacion"
            },
            headers=headers
        )
        assert create_resp.status_code == 200
        draft = create_resp.json()
        
        # Confirm
        response = requests.post(
            f"{BASE_URL}/api/transferencias-linea/{draft['id']}/confirmar",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["estado"] == "CONFIRMADO"
        assert "costo_total_transferido" in data
        assert "capas_consumidas" in data
        assert "salida_id" in data
        
        print(f"Confirmed: {data['codigo']}, costo={data['costo_total_transferido']}, capas={data['capas_consumidas']}")
    
    def test_confirmar_transferencia_not_found(self, headers):
        """Returns 404 for non-existent transfer"""
        fake_id = str(uuid.uuid4())
        response = requests.post(
            f"{BASE_URL}/api/transferencias-linea/{fake_id}/confirmar",
            headers=headers
        )
        assert response.status_code == 404
    
    def test_confirmar_transferencia_already_confirmed(self, headers):
        """Returns 400 when trying to confirm already confirmed transfer"""
        # Find a confirmed transfer
        list_resp = requests.get(
            f"{BASE_URL}/api/transferencias-linea?estado=CONFIRMADO&limit=1",
            headers=headers
        )
        list_data = list_resp.json()
        
        if not list_data["items"]:
            pytest.skip("No confirmed transfers available for testing")
        
        transfer_id = list_data["items"][0]["id"]
        
        response = requests.post(
            f"{BASE_URL}/api/transferencias-linea/{transfer_id}/confirmar",
            headers=headers
        )
        assert response.status_code == 400
        assert "borrador" in response.json()["detail"].lower()


class TestCancelarTransferencia:
    """Tests for POST /api/transferencias-linea/{id}/cancelar"""
    
    def test_cancelar_borrador_success(self, headers):
        """Cancel a draft transfer"""
        # First get available stock
        stock_resp = requests.get(
            f"{BASE_URL}/api/transferencias-linea/stock-por-linea/{TEST_ITEM_ID}",
            headers=headers
        )
        stock_data = stock_resp.json()
        
        # Find a linea with stock
        linea_con_stock = None
        for l in stock_data.get("lineas", []):
            if l["stock_disponible"] > 0:
                linea_con_stock = l
                break
        
        if not linea_con_stock:
            pytest.skip("No stock available for testing cancellation")
        
        # Find a different linea for destino
        linea_destino_id = TEST_LINEA_DESTINO
        if linea_destino_id == linea_con_stock["linea_negocio_id"]:
            linea_destino_id = 28
        
        # Create draft
        create_resp = requests.post(
            f"{BASE_URL}/api/transferencias-linea",
            json={
                "item_id": TEST_ITEM_ID,
                "linea_origen_id": linea_con_stock["linea_negocio_id"],
                "linea_destino_id": linea_destino_id,
                "cantidad": 0.1,
                "motivo": "TEST - Para cancelar"
            },
            headers=headers
        )
        assert create_resp.status_code == 200
        draft = create_resp.json()
        
        # Cancel
        response = requests.post(
            f"{BASE_URL}/api/transferencias-linea/{draft['id']}/cancelar",
            json={"motivo_cancelacion": "Cancelado por prueba automatizada"},
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["estado"] == "CANCELADO"
        print(f"Cancelled: {data['codigo']}")
    
    def test_cancelar_transferencia_not_found(self, headers):
        """Returns 404 for non-existent transfer"""
        fake_id = str(uuid.uuid4())
        response = requests.post(
            f"{BASE_URL}/api/transferencias-linea/{fake_id}/cancelar",
            json={"motivo_cancelacion": "Test"},
            headers=headers
        )
        assert response.status_code == 404
    
    def test_cancelar_transferencia_already_confirmed(self, headers):
        """Returns 400 when trying to cancel confirmed transfer"""
        # Find a confirmed transfer
        list_resp = requests.get(
            f"{BASE_URL}/api/transferencias-linea?estado=CONFIRMADO&limit=1",
            headers=headers
        )
        list_data = list_resp.json()
        
        if not list_data["items"]:
            pytest.skip("No confirmed transfers available for testing")
        
        transfer_id = list_data["items"][0]["id"]
        
        response = requests.post(
            f"{BASE_URL}/api/transferencias-linea/{transfer_id}/cancelar",
            json={"motivo_cancelacion": "Test"},
            headers=headers
        )
        assert response.status_code == 400
        assert "borrador" in response.json()["detail"].lower()


class TestLineasNegocio:
    """Tests for GET /api/lineas-negocio - Required for frontend dropdown"""
    
    def test_list_lineas_negocio(self, headers):
        """List business lines for dropdown"""
        response = requests.get(
            f"{BASE_URL}/api/lineas-negocio",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # Verify expected lineas exist
        linea_ids = [l["id"] for l in data]
        assert 26 in linea_ids or "26" in [str(l["id"]) for l in data]  # Pantalon denim
        
        print(f"Found {len(data)} lineas de negocio")
        for l in data[:5]:
            print(f"  - {l.get('id')}: {l.get('nombre')}")


class TestInventarioItems:
    """Tests for GET /api/inventario - Required for frontend item selection"""
    
    def test_list_inventario_items(self, headers):
        """List inventory items for dropdown"""
        response = requests.get(
            f"{BASE_URL}/api/inventario?all=true",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # Verify test item exists
        item_ids = [i["id"] for i in data]
        assert TEST_ITEM_ID in item_ids
        
        print(f"Found {len(data)} inventory items")
