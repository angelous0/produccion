"""
Pytest Test Suite for BOM Module (Cabecera + Lineas + Costo Estándar)
Tests the new BOM system with:
- prod_bom_cabecera: id, modelo_id, codigo, version, estado, vigente_desde, vigente_hasta, observaciones
- prod_modelo_bom_linea extended with: bom_id, tipo_componente, merma_pct, cantidad_total, es_opcional, etapa_id

Endpoints tested:
- GET /api/bom?modelo_id={id} - Lista cabeceras BOM
- POST /api/bom - Crear nueva cabecera BOM
- GET /api/bom/{bom_id} - Detalle cabecera con líneas
- PUT /api/bom/{bom_id} - Cambiar estado (BORRADOR->APROBADO->INACTIVO)
- POST /api/bom/{bom_id}/lineas - Agregar línea con tipo_componente
- PUT /api/bom/{bom_id}/lineas/{linea_id} - Actualizar línea
- DELETE /api/bom/{bom_id}/lineas/{linea_id} - Eliminar línea
- GET /api/bom/{bom_id}/costo-estandar?cantidad_prendas=100 - Cálculo costo estándar
- POST /api/bom/{bom_id}/duplicar - Duplica BOM con nueva versión

empresa_id=7 for all queries
"""
import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
EMPRESA_ID = 7

# Test credentials
USERNAME = "eduard"
PASSWORD = "eduard123"

# Known test data from context
MODELO_ID = "f5d3b229-7a6b-4d62-888d-80f60c3b1f73"
EXISTING_BOM_ID = "db92cc93-d42e-4038-abe6-f2e18ac4e68e"  # BOM-EDUARD-V1, 10 lineas
INVENTARIO_TELA_ID = "91135a62-b4d5-4df9-8516-c64709f77b91"  # Tela Algodón, costo=5.50
INVENTARIO_AVIO_ID = "cabbd10c-84c9-49b4-9610-deef3a573fa6"  # Boton Pretinero, costo=1.0

# Track created test data for cleanup
CREATED_BOM_IDS = []
CREATED_LINEA_IDS = []


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def auth_token(api_client):
    """Get authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "username": USERNAME,
        "password": PASSWORD
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    token = response.json().get("access_token")
    assert token, "No access token returned"
    return token


@pytest.fixture(scope="module")
def authenticated_client(api_client, auth_token):
    """Session with auth header"""
    api_client.headers.update({"Authorization": f"Bearer {auth_token}"})
    return api_client


# ==================== LIST BOM CABECERAS ====================

class TestListBOMCabeceras:
    """Tests for GET /api/bom?modelo_id={id}"""
    
    def test_list_bom_cabeceras_success(self, authenticated_client):
        """List BOMs for a specific modelo"""
        response = authenticated_client.get(f"{BASE_URL}/api/bom?modelo_id={MODELO_ID}")
        assert response.status_code == 200, f"List BOMs failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        # Check structure if there are BOMs
        if data:
            bom = data[0]
            required_fields = ["id", "modelo_id", "codigo", "version", "estado", "total_lineas"]
            for field in required_fields:
                assert field in bom, f"BOM cabecera missing field: {field}"
            
            # Verify version ordering (DESC)
            if len(data) > 1:
                assert data[0]["version"] >= data[1]["version"], "BOMs should be ordered by version DESC"
    
    def test_list_bom_requires_modelo_id(self, authenticated_client):
        """modelo_id is required parameter"""
        response = authenticated_client.get(f"{BASE_URL}/api/bom")
        assert response.status_code == 422, f"Expected 422 without modelo_id, got {response.status_code}"
    
    def test_list_bom_with_estado_filter(self, authenticated_client):
        """Can filter BOMs by estado"""
        response = authenticated_client.get(f"{BASE_URL}/api/bom?modelo_id={MODELO_ID}&estado=BORRADOR")
        assert response.status_code == 200, f"Filter by estado failed: {response.text}"
        
        data = response.json()
        for bom in data:
            assert bom["estado"] == "BORRADOR", f"Filter should return only BORRADOR BOMs"


# ==================== CREATE BOM CABECERA ====================

class TestCreateBOMCabecera:
    """Tests for POST /api/bom"""
    
    def test_create_bom_cabecera_success(self, authenticated_client):
        """Create new BOM cabecera for a modelo"""
        # First get current max version
        list_response = authenticated_client.get(f"{BASE_URL}/api/bom?modelo_id={MODELO_ID}")
        assert list_response.status_code == 200
        existing_boms = list_response.json()
        max_version = max([b["version"] for b in existing_boms]) if existing_boms else 0
        
        # Create new BOM
        response = authenticated_client.post(f"{BASE_URL}/api/bom", json={
            "modelo_id": MODELO_ID,
            "observaciones": "TEST - BOM creado por pytest"
        })
        assert response.status_code == 200, f"Create BOM failed: {response.text}"
        
        data = response.json()
        assert "id" in data
        assert data["modelo_id"] == MODELO_ID
        assert data["estado"] == "BORRADOR"  # New BOMs start as BORRADOR
        assert data["version"] == max_version + 1  # Auto-incremented version
        assert "codigo" in data  # Auto-generated codigo
        
        CREATED_BOM_IDS.append(data["id"])
        print(f"Created BOM with id={data['id']}, version={data['version']}")
    
    def test_create_bom_for_invalid_modelo_returns_404(self, authenticated_client):
        """Creating BOM for non-existent modelo returns 404"""
        fake_modelo_id = "00000000-0000-0000-0000-000000000000"
        response = authenticated_client.post(f"{BASE_URL}/api/bom", json={
            "modelo_id": fake_modelo_id
        })
        assert response.status_code == 404, f"Expected 404 for invalid modelo, got {response.status_code}"


# ==================== GET BOM DETALLE ====================

class TestGetBOMDetalle:
    """Tests for GET /api/bom/{bom_id}"""
    
    def test_get_bom_detalle_success(self, authenticated_client):
        """Get BOM cabecera with lines"""
        response = authenticated_client.get(f"{BASE_URL}/api/bom/{EXISTING_BOM_ID}")
        assert response.status_code == 200, f"Get BOM detalle failed: {response.text}"
        
        data = response.json()
        
        # Check cabecera fields
        cabecera_fields = ["id", "modelo_id", "codigo", "version", "estado", "modelo_nombre"]
        for field in cabecera_fields:
            assert field in data, f"BOM detalle missing cabecera field: {field}"
        
        # Check lineas array
        assert "lineas" in data, "BOM detalle must include 'lineas' array"
        assert isinstance(data["lineas"], list)
        
        # Check linea structure if present
        if data["lineas"]:
            linea = data["lineas"][0]
            linea_fields = ["id", "inventario_id", "tipo_componente", "cantidad_base", 
                          "merma_pct", "cantidad_total", "es_opcional", "activo"]
            for field in linea_fields:
                assert field in linea, f"BOM linea missing field: {field}"
            
            # Check inventario_nombre is populated
            assert "inventario_nombre" in linea, "Linea should have inventario_nombre"
    
    def test_get_bom_detalle_invalid_returns_404(self, authenticated_client):
        """Get non-existent BOM returns 404"""
        fake_bom_id = "00000000-0000-0000-0000-000000000000"
        response = authenticated_client.get(f"{BASE_URL}/api/bom/{fake_bom_id}")
        assert response.status_code == 404


# ==================== UPDATE BOM ESTADO ====================

class TestUpdateBOMEstado:
    """Tests for PUT /api/bom/{bom_id}"""
    
    def test_update_bom_estado_borrador_to_aprobado(self, authenticated_client):
        """Change estado from BORRADOR to APROBADO"""
        # Create a new BOM in BORRADOR state
        create_response = authenticated_client.post(f"{BASE_URL}/api/bom", json={
            "modelo_id": MODELO_ID,
            "observaciones": "TEST - BOM para cambio de estado"
        })
        assert create_response.status_code == 200
        bom_id = create_response.json()["id"]
        CREATED_BOM_IDS.append(bom_id)
        
        # Change to APROBADO
        response = authenticated_client.put(f"{BASE_URL}/api/bom/{bom_id}", json={
            "estado": "APROBADO"
        })
        assert response.status_code == 200, f"Update estado failed: {response.text}"
        
        data = response.json()
        assert data["estado"] == "APROBADO"
    
    def test_update_bom_estado_aprobado_to_inactivo(self, authenticated_client):
        """Change estado from APROBADO to INACTIVO"""
        # Create and approve BOM
        create_response = authenticated_client.post(f"{BASE_URL}/api/bom", json={
            "modelo_id": MODELO_ID,
            "observaciones": "TEST - BOM para inactivar"
        })
        assert create_response.status_code == 200
        bom_id = create_response.json()["id"]
        CREATED_BOM_IDS.append(bom_id)
        
        # Approve first
        authenticated_client.put(f"{BASE_URL}/api/bom/{bom_id}", json={"estado": "APROBADO"})
        
        # Then inactivate
        response = authenticated_client.put(f"{BASE_URL}/api/bom/{bom_id}", json={
            "estado": "INACTIVO"
        })
        assert response.status_code == 200
        assert response.json()["estado"] == "INACTIVO"
    
    def test_update_bom_invalid_estado_fails(self, authenticated_client):
        """Invalid estado should fail with 400"""
        if not CREATED_BOM_IDS:
            pytest.skip("No test BOM available")
        
        response = authenticated_client.put(f"{BASE_URL}/api/bom/{CREATED_BOM_IDS[0]}", json={
            "estado": "INVALID_ESTADO"
        })
        assert response.status_code == 400, f"Expected 400 for invalid estado, got {response.status_code}"


# ==================== BOM LINEAS CRUD ====================

class TestBOMLineas:
    """Tests for BOM lineas CRUD operations"""
    
    def test_add_linea_tipo_tela(self, authenticated_client):
        """Add linea with tipo_componente=TELA"""
        # Create BOM for testing
        create_response = authenticated_client.post(f"{BASE_URL}/api/bom", json={
            "modelo_id": MODELO_ID,
            "observaciones": "TEST - BOM para lineas"
        })
        assert create_response.status_code == 200
        bom_id = create_response.json()["id"]
        CREATED_BOM_IDS.append(bom_id)
        
        # Add linea
        response = authenticated_client.post(f"{BASE_URL}/api/bom/{bom_id}/lineas", json={
            "inventario_id": INVENTARIO_TELA_ID,
            "tipo_componente": "TELA",
            "cantidad_base": 1.5,
            "merma_pct": 5.0,
            "es_opcional": False
        })
        assert response.status_code == 200, f"Add linea failed: {response.text}"
        
        data = response.json()
        assert data["tipo_componente"] == "TELA"
        assert data["cantidad_base"] == 1.5
        assert data["merma_pct"] == 5.0
        # Check cantidad_total = cantidad_base * (1 + merma_pct/100)
        expected_total = round(1.5 * (1 + 5.0/100), 4)
        assert abs(float(data["cantidad_total"]) - expected_total) < 0.0001, \
            f"cantidad_total should be {expected_total}, got {data['cantidad_total']}"
        
        CREATED_LINEA_IDS.append(data["id"])
    
    def test_add_linea_tipo_avio(self, authenticated_client):
        """Add linea with tipo_componente=AVIO"""
        if not CREATED_BOM_IDS:
            pytest.skip("No test BOM available")
        
        bom_id = CREATED_BOM_IDS[-1]
        
        response = authenticated_client.post(f"{BASE_URL}/api/bom/{bom_id}/lineas", json={
            "inventario_id": INVENTARIO_AVIO_ID,
            "tipo_componente": "AVIO",
            "cantidad_base": 4.0,
            "merma_pct": 0,
            "es_opcional": False
        })
        assert response.status_code == 200
        
        data = response.json()
        assert data["tipo_componente"] == "AVIO"
        # No merma: cantidad_total == cantidad_base
        assert float(data["cantidad_total"]) == 4.0
        
        CREATED_LINEA_IDS.append(data["id"])
    
    def test_add_linea_validates_cantidad_base(self, authenticated_client):
        """cantidad_base must be > 0"""
        if not CREATED_BOM_IDS:
            pytest.skip("No test BOM available")
        
        bom_id = CREATED_BOM_IDS[-1]
        
        response = authenticated_client.post(f"{BASE_URL}/api/bom/{bom_id}/lineas", json={
            "inventario_id": INVENTARIO_TELA_ID,
            "tipo_componente": "TELA",
            "cantidad_base": 0,  # Invalid
            "merma_pct": 5.0
        })
        assert response.status_code == 400, f"Expected 400 for cantidad_base=0, got {response.status_code}"
    
    def test_add_linea_validates_merma_pct(self, authenticated_client):
        """merma_pct must be 0-100"""
        if not CREATED_BOM_IDS:
            pytest.skip("No test BOM available")
        
        bom_id = CREATED_BOM_IDS[-1]
        
        response = authenticated_client.post(f"{BASE_URL}/api/bom/{bom_id}/lineas", json={
            "inventario_id": INVENTARIO_TELA_ID,
            "tipo_componente": "TELA",
            "cantidad_base": 1.0,
            "merma_pct": 150.0  # Invalid
        })
        assert response.status_code == 400, f"Expected 400 for merma_pct=150, got {response.status_code}"
    
    def test_add_linea_validates_tipo_componente(self, authenticated_client):
        """tipo_componente must be valid"""
        if not CREATED_BOM_IDS:
            pytest.skip("No test BOM available")
        
        bom_id = CREATED_BOM_IDS[-1]
        
        response = authenticated_client.post(f"{BASE_URL}/api/bom/{bom_id}/lineas", json={
            "inventario_id": INVENTARIO_TELA_ID,
            "tipo_componente": "INVALID_TIPO",  # Invalid
            "cantidad_base": 1.0,
            "merma_pct": 5.0
        })
        assert response.status_code == 400, f"Expected 400 for invalid tipo, got {response.status_code}"
    
    def test_update_linea_success(self, authenticated_client):
        """Update BOM linea"""
        if not CREATED_BOM_IDS or not CREATED_LINEA_IDS:
            pytest.skip("No test data available")
        
        bom_id = CREATED_BOM_IDS[-1]
        linea_id = CREATED_LINEA_IDS[0]
        
        response = authenticated_client.put(f"{BASE_URL}/api/bom/{bom_id}/lineas/{linea_id}", json={
            "cantidad_base": 2.0,
            "merma_pct": 10.0,
            "es_opcional": True
        })
        assert response.status_code == 200, f"Update linea failed: {response.text}"
        
        data = response.json()
        assert data["cantidad_base"] == 2.0
        assert data["merma_pct"] == 10.0
        assert data["es_opcional"] == True
        # Check recalculated cantidad_total
        expected_total = round(2.0 * (1 + 10.0/100), 4)
        assert abs(float(data["cantidad_total"]) - expected_total) < 0.0001
    
    def test_delete_linea_success(self, authenticated_client):
        """Delete BOM linea"""
        # Create a linea to delete
        if not CREATED_BOM_IDS:
            pytest.skip("No test BOM available")
        
        bom_id = CREATED_BOM_IDS[-1]
        
        # Create linea
        create_response = authenticated_client.post(f"{BASE_URL}/api/bom/{bom_id}/lineas", json={
            "inventario_id": INVENTARIO_TELA_ID,
            "tipo_componente": "EMPAQUE",
            "cantidad_base": 1.0,
            "merma_pct": 0
        })
        if create_response.status_code != 200:
            pytest.skip("Could not create linea for delete test")
        
        linea_id = create_response.json()["id"]
        
        # Delete linea
        response = authenticated_client.delete(f"{BASE_URL}/api/bom/{bom_id}/lineas/{linea_id}")
        assert response.status_code == 200, f"Delete linea failed: {response.text}"
        
        # Verify deletion
        get_response = authenticated_client.get(f"{BASE_URL}/api/bom/{bom_id}")
        assert get_response.status_code == 200
        lineas = get_response.json()["lineas"]
        linea_ids = [l["id"] for l in lineas]
        assert linea_id not in linea_ids, "Deleted linea should not appear"


# ==================== COSTO ESTÁNDAR ====================

class TestCostoEstandar:
    """Tests for GET /api/bom/{bom_id}/costo-estandar"""
    
    def test_costo_estandar_success(self, authenticated_client):
        """Get costo estándar for a BOM"""
        response = authenticated_client.get(f"{BASE_URL}/api/bom/{EXISTING_BOM_ID}/costo-estandar?cantidad_prendas=100")
        assert response.status_code == 200, f"Get costo estandar failed: {response.text}"
        
        data = response.json()
        
        # Check response structure
        required_fields = ["bom_id", "modelo_id", "version", "estado", "cantidad_prendas",
                         "costo_estandar_unitario", "costo_estandar_lote", "costo_por_tipo", "detalle"]
        for field in required_fields:
            assert field in data, f"Costo estándar missing field: {field}"
        
        assert data["cantidad_prendas"] == 100
        assert isinstance(data["costo_estandar_unitario"], (int, float))
        assert isinstance(data["costo_estandar_lote"], (int, float))
        
        # Validate costo_por_tipo
        assert isinstance(data["costo_por_tipo"], dict)
    
    def test_costo_estandar_detalle_structure(self, authenticated_client):
        """Detalle should include all required fields"""
        response = authenticated_client.get(f"{BASE_URL}/api/bom/{EXISTING_BOM_ID}/costo-estandar?cantidad_prendas=1")
        assert response.status_code == 200
        
        data = response.json()
        
        if data["detalle"]:
            item = data["detalle"][0]
            required_fields = ["linea_id", "inventario_nombre", "tipo_componente", 
                             "cantidad_base", "merma_pct", "cantidad_total",
                             "precio_unitario", "costo_por_prenda", "costo_lote", "es_opcional"]
            for field in required_fields:
                assert field in item, f"Detalle item missing field: {field}"
    
    def test_costo_estandar_calculation(self, authenticated_client):
        """Verify costo calculation: costo_lote = costo_unitario * cantidad_prendas"""
        response = authenticated_client.get(f"{BASE_URL}/api/bom/{EXISTING_BOM_ID}/costo-estandar?cantidad_prendas=50")
        assert response.status_code == 200
        
        data = response.json()
        
        # costo_estandar_lote should be costo_estandar_unitario * cantidad_prendas
        expected_lote = round(data["costo_estandar_unitario"] * 50, 2)
        assert abs(data["costo_estandar_lote"] - expected_lote) < 0.01, \
            f"Lote calculation wrong: expected {expected_lote}, got {data['costo_estandar_lote']}"
    
    def test_costo_estandar_excludes_optional(self, authenticated_client):
        """Optional items should not be included in total"""
        # Test with existing BOM - verify logic
        response = authenticated_client.get(f"{BASE_URL}/api/bom/{EXISTING_BOM_ID}/costo-estandar?cantidad_prendas=1")
        assert response.status_code == 200
        
        data = response.json()
        
        # Calculate sum of non-optional items
        non_optional_sum = sum(
            item["costo_por_prenda"] 
            for item in data["detalle"] 
            if not item.get("es_opcional", False)
        )
        
        # Should match costo_estandar_unitario
        assert abs(non_optional_sum - data["costo_estandar_unitario"]) < 0.01, \
            f"Total should exclude optional items"


# ==================== DUPLICAR BOM ====================

class TestDuplicarBOM:
    """Tests for POST /api/bom/{bom_id}/duplicar"""
    
    def test_duplicar_bom_success(self, authenticated_client):
        """Duplicate BOM creates new version with copied lines"""
        # Get current max version
        list_response = authenticated_client.get(f"{BASE_URL}/api/bom?modelo_id={MODELO_ID}")
        assert list_response.status_code == 200
        existing_boms = list_response.json()
        max_version = max([b["version"] for b in existing_boms]) if existing_boms else 0
        
        # Duplicate existing BOM
        response = authenticated_client.post(f"{BASE_URL}/api/bom/{EXISTING_BOM_ID}/duplicar")
        assert response.status_code == 200, f"Duplicar BOM failed: {response.text}"
        
        data = response.json()
        assert data["version"] == max_version + 1
        assert data["estado"] == "BORRADOR"  # Duplicated BOMs start as BORRADOR
        assert data["modelo_id"] == MODELO_ID
        assert "total_lineas" in data
        
        CREATED_BOM_IDS.append(data["id"])
        
        # Verify lines were copied
        get_response = authenticated_client.get(f"{BASE_URL}/api/bom/{data['id']}")
        assert get_response.status_code == 200
        duplicated = get_response.json()
        
        # Get original BOM lines count
        orig_response = authenticated_client.get(f"{BASE_URL}/api/bom/{EXISTING_BOM_ID}")
        original = orig_response.json()
        original_active_lines = len([l for l in original["lineas"] if l.get("activo", True)])
        
        # Duplicated should have same number of active lines
        duplicated_lines = len(duplicated["lineas"])
        assert duplicated_lines == original_active_lines, \
            f"Duplicated BOM should have {original_active_lines} lines, got {duplicated_lines}"
    
    def test_duplicar_invalid_bom_returns_404(self, authenticated_client):
        """Duplicate non-existent BOM returns 404"""
        fake_bom_id = "00000000-0000-0000-0000-000000000000"
        response = authenticated_client.post(f"{BASE_URL}/api/bom/{fake_bom_id}/duplicar")
        assert response.status_code == 404


# ==================== cantidad_total CALCULATION ====================

class TestCantidadTotalCalculation:
    """Verify cantidad_total = cantidad_base * (1 + merma_pct/100)"""
    
    def test_cantidad_total_with_merma(self, authenticated_client):
        """Test cantidad_total calculation with different merma values"""
        if not CREATED_BOM_IDS:
            # Create a BOM for this test
            create_response = authenticated_client.post(f"{BASE_URL}/api/bom", json={
                "modelo_id": MODELO_ID,
                "observaciones": "TEST - BOM for cantidad_total test"
            })
            assert create_response.status_code == 200
            bom_id = create_response.json()["id"]
            CREATED_BOM_IDS.append(bom_id)
        else:
            bom_id = CREATED_BOM_IDS[-1]
        
        test_cases = [
            {"cantidad_base": 2.0, "merma_pct": 0, "expected": 2.0},
            {"cantidad_base": 2.0, "merma_pct": 10.0, "expected": 2.2},
            {"cantidad_base": 1.5, "merma_pct": 20.0, "expected": 1.8},
            {"cantidad_base": 3.0, "merma_pct": 5.0, "expected": 3.15},
        ]
        
        for case in test_cases:
            response = authenticated_client.post(f"{BASE_URL}/api/bom/{bom_id}/lineas", json={
                "inventario_id": INVENTARIO_TELA_ID,
                "tipo_componente": "OTRO",
                "cantidad_base": case["cantidad_base"],
                "merma_pct": case["merma_pct"]
            })
            
            if response.status_code == 200:
                data = response.json()
                CREATED_LINEA_IDS.append(data["id"])
                
                actual = float(data["cantidad_total"])
                assert abs(actual - case["expected"]) < 0.0001, \
                    f"cantidad_total wrong for base={case['cantidad_base']}, merma={case['merma_pct']}: expected {case['expected']}, got {actual}"


# ==================== REPORTS NON-REGRESSION ====================

class TestReportsNonRegression:
    """Verify production reports still work correctly"""
    
    def test_wip_report_still_works(self, authenticated_client):
        """WIP report should still return correct data"""
        response = authenticated_client.get(f"{BASE_URL}/api/reportes/wip?empresa_id={EMPRESA_ID}")
        assert response.status_code == 200, f"WIP report broken: {response.text}"
        
        data = response.json()
        assert "ordenes" in data
        assert "resumen" in data
    
    def test_mp_valorizado_still_works(self, authenticated_client):
        """MP Valorizado report should still return correct data"""
        response = authenticated_client.get(f"{BASE_URL}/api/reportes/mp-valorizado?empresa_id={EMPRESA_ID}")
        assert response.status_code == 200, f"MP report broken: {response.text}"
        
        data = response.json()
        assert "items" in data
        assert "resumen" in data
    
    def test_pt_valorizado_still_works(self, authenticated_client):
        """PT Valorizado report should still return correct data"""
        response = authenticated_client.get(f"{BASE_URL}/api/reportes/pt-valorizado?empresa_id={EMPRESA_ID}")
        assert response.status_code == 200, f"PT report broken: {response.text}"
        
        data = response.json()
        assert "items" in data
        assert "resumen" in data
    
    def test_resumen_general_still_works(self, authenticated_client):
        """Resumen general should still return correct data"""
        response = authenticated_client.get(f"{BASE_URL}/api/reportes/resumen-general?empresa_id={EMPRESA_ID}")
        assert response.status_code == 200, f"Resumen general broken: {response.text}"
        
        data = response.json()
        assert "inventario" in data
        assert "ordenes" in data


# ==================== ETAPAS ENDPOINT ====================

class TestEtapasEndpoint:
    """Test etapas endpoint for BOM line assignments"""
    
    def test_get_etapas(self, authenticated_client):
        """GET /api/etapas returns etapas for empresa"""
        response = authenticated_client.get(f"{BASE_URL}/api/etapas?empresa_id={EMPRESA_ID}")
        assert response.status_code == 200, f"Get etapas failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Etapas should be a list"


# ==================== CLEANUP ====================

@pytest.fixture(scope="module", autouse=True)
def cleanup_test_data(authenticated_client):
    """Cleanup test-created data after all tests"""
    yield
    
    # Clean up created BOMs (which cascade deletes lineas)
    for bom_id in CREATED_BOM_IDS:
        try:
            # Delete lineas first
            get_response = authenticated_client.get(f"{BASE_URL}/api/bom/{bom_id}")
            if get_response.status_code == 200:
                for linea in get_response.json().get("lineas", []):
                    authenticated_client.delete(f"{BASE_URL}/api/bom/{bom_id}/lineas/{linea['id']}")
            
            # Note: No DELETE endpoint for BOM cabecera, so we'll mark it as INACTIVO
            authenticated_client.put(f"{BASE_URL}/api/bom/{bom_id}", json={
                "estado": "INACTIVO",
                "observaciones": "TEST - Marcado inactivo por cleanup"
            })
        except:
            pass
    
    print(f"\nCleanup: Marked {len(CREATED_BOM_IDS)} test BOMs as INACTIVO")
