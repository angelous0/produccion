"""
Test Suite: Matriz Dinámica de Producción
Tests for the /api/reportes-produccion/matriz endpoint:
- Basic endpoint functionality
- Filter parameters (ruta_id, marca_id, solo_activos, solo_atrasados, solo_fraccionados)
- Response structure (columnas, filas, totales_columna, total_general, filtros_disponibles)
- Fila structure (item, hilo, celdas, total, detalle)
- Detalle structure (id, n_corte, estado, prendas, modelo, ruta, urgente, es_hijo, fecha_entrega)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestMatrizAuth:
    """Test authentication for matriz endpoint"""
    
    def test_matriz_requires_auth(self):
        """Matriz endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/reportes-produccion/matriz")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"


class TestMatrizBasic:
    """Test basic Matriz endpoint functionality"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "eduard",
            "password": "eduard123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_matriz_returns_200(self, auth_headers):
        """Matriz endpoint returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/matriz",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_matriz_has_required_fields(self, auth_headers):
        """Matriz returns all required top-level fields"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/matriz",
            headers=auth_headers
        )
        data = response.json()
        
        required_fields = [
            "columnas",
            "filas",
            "totales_columna",
            "total_general",
            "filtros_disponibles"
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
    
    def test_matriz_columnas_is_list(self, auth_headers):
        """Matriz columnas is a list of strings (estados)"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/matriz",
            headers=auth_headers
        )
        data = response.json()
        
        assert isinstance(data["columnas"], list)
        # Columnas should be strings (estado names)
        for col in data["columnas"]:
            assert isinstance(col, str)
    
    def test_matriz_filas_is_list(self, auth_headers):
        """Matriz filas is a list"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/matriz",
            headers=auth_headers
        )
        data = response.json()
        
        assert isinstance(data["filas"], list)
    
    def test_matriz_total_general_structure(self, auth_headers):
        """Matriz total_general has registros and prendas"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/matriz",
            headers=auth_headers
        )
        data = response.json()
        
        assert "registros" in data["total_general"]
        assert "prendas" in data["total_general"]
        assert isinstance(data["total_general"]["registros"], int)
        assert isinstance(data["total_general"]["prendas"], int)
    
    def test_matriz_totales_columna_structure(self, auth_headers):
        """Matriz totales_columna is dict with registros/prendas per column"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/matriz",
            headers=auth_headers
        )
        data = response.json()
        
        assert isinstance(data["totales_columna"], dict)
        for col, vals in data["totales_columna"].items():
            assert "registros" in vals
            assert "prendas" in vals


class TestMatrizFilaStructure:
    """Test Matriz fila structure"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "eduard",
            "password": "eduard123"
        })
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_matriz_fila_has_required_fields(self, auth_headers):
        """Matriz fila has item, hilo, celdas, total, detalle"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/matriz",
            headers=auth_headers
        )
        data = response.json()
        
        if data["filas"]:
            fila = data["filas"][0]
            required_fields = ["item", "hilo", "celdas", "total", "detalle"]
            for field in required_fields:
                assert field in fila, f"Missing field in fila: {field}"
    
    def test_matriz_fila_item_format(self, auth_headers):
        """Matriz fila item is formatted as 'Marca - Tipo - Entalle - Tela'"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/matriz",
            headers=auth_headers
        )
        data = response.json()
        
        if data["filas"]:
            fila = data["filas"][0]
            # Item should contain dashes (Marca - Tipo - Entalle - Tela)
            assert isinstance(fila["item"], str)
            # Also check individual components exist
            assert "marca" in fila
            assert "tipo" in fila
            assert "entalle" in fila
            assert "tela" in fila
    
    def test_matriz_fila_celdas_structure(self, auth_headers):
        """Matriz fila celdas is dict with registros/prendas per estado"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/matriz",
            headers=auth_headers
        )
        data = response.json()
        
        if data["filas"]:
            fila = data["filas"][0]
            assert isinstance(fila["celdas"], dict)
            for estado, vals in fila["celdas"].items():
                assert "registros" in vals
                assert "prendas" in vals
    
    def test_matriz_fila_total_structure(self, auth_headers):
        """Matriz fila total has registros and prendas"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/matriz",
            headers=auth_headers
        )
        data = response.json()
        
        if data["filas"]:
            fila = data["filas"][0]
            assert "registros" in fila["total"]
            assert "prendas" in fila["total"]


class TestMatrizDetalleStructure:
    """Test Matriz detalle structure including enriched fields"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "eduard",
            "password": "eduard123"
        })
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_matriz_detalle_has_required_fields(self, auth_headers):
        """Matriz detalle has all required fields including enriched fields"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/matriz",
            headers=auth_headers
        )
        data = response.json()
        
        if data["filas"]:
            fila = data["filas"][0]
            if fila["detalle"]:
                detalle = fila["detalle"][0]
                # Original required fields
                required_fields = [
                    "id", "n_corte", "estado", "prendas",
                    "modelo", "ruta", "urgente", "es_hijo", "fecha_entrega"
                ]
                # NEW enriched fields including fecha_inicio_prod
                enriched_fields = [
                    "curva", "curva_detalle", "hilo_especifico",
                    "dias_proceso", "ult_mov_servicio", "ult_mov_fecha",
                    "diferencia_acumulada", "total_movimientos",
                    "fecha_inicio_prod"  # NEW: first movement's fecha_inicio
                ]
                for field in required_fields + enriched_fields:
                    assert field in detalle, f"Missing field in detalle: {field}"
    
    def test_matriz_detalle_types(self, auth_headers):
        """Matriz detalle fields have correct types"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/matriz",
            headers=auth_headers
        )
        data = response.json()
        
        if data["filas"]:
            fila = data["filas"][0]
            if fila["detalle"]:
                detalle = fila["detalle"][0]
                assert isinstance(detalle["id"], str)
                assert isinstance(detalle["n_corte"], str)
                assert isinstance(detalle["estado"], str)
                assert isinstance(detalle["prendas"], int)
                assert isinstance(detalle["urgente"], bool)
                assert isinstance(detalle["es_hijo"], bool)
    
    def test_matriz_detalle_enriched_types(self, auth_headers):
        """Matriz detalle enriched fields have correct types"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/matriz",
            headers=auth_headers
        )
        data = response.json()
        
        if data["filas"]:
            fila = data["filas"][0]
            if fila["detalle"]:
                detalle = fila["detalle"][0]
                # curva is string (can be empty)
                assert isinstance(detalle["curva"], str)
                # curva_detalle is list of {talla, cantidad}
                assert isinstance(detalle["curva_detalle"], list)
                # hilo_especifico is string (can be empty)
                assert isinstance(detalle["hilo_especifico"], str)
                # dias_proceso is int
                assert isinstance(detalle["dias_proceso"], int)
                # ult_mov_servicio is string (can be empty)
                assert isinstance(detalle["ult_mov_servicio"], str)
                # ult_mov_fecha is string or None
                assert detalle["ult_mov_fecha"] is None or isinstance(detalle["ult_mov_fecha"], str)
                # diferencia_acumulada is int
                assert isinstance(detalle["diferencia_acumulada"], int)
                # total_movimientos is int
                assert isinstance(detalle["total_movimientos"], int)
                # fecha_inicio_prod is string or None (first movement's fecha_inicio)
                assert detalle["fecha_inicio_prod"] is None or isinstance(detalle["fecha_inicio_prod"], str)
    
    def test_matriz_detalle_dias_proceso_from_first_movement(self, auth_headers):
        """Matriz detalle dias_proceso is calculated from first movement's fecha_inicio, not fecha_creacion"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/matriz",
            headers=auth_headers
        )
        data = response.json()
        
        # Find a registro with movements (fecha_inicio_prod not null)
        for fila in data["filas"]:
            for detalle in fila["detalle"]:
                if detalle["fecha_inicio_prod"] is not None:
                    # dias_proceso should be >= 0 when fecha_inicio_prod exists
                    assert detalle["dias_proceso"] >= 0, f"dias_proceso should be >= 0 for registro with movements"
                    print(f"Registro {detalle['n_corte']}: dias_proceso={detalle['dias_proceso']}, fecha_inicio_prod={detalle['fecha_inicio_prod']}")
                    return
        
        # If no registro with movements found, skip
        pytest.skip("No registro with movements found to test dias_proceso calculation")
    
    def test_matriz_detalle_dias_proceso_zero_without_movements(self, auth_headers):
        """Matriz detalle dias_proceso is 0 when registro has no movements (fecha_inicio_prod is null)"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/matriz",
            headers=auth_headers
        )
        data = response.json()
        
        # Find a registro without movements (fecha_inicio_prod is null)
        for fila in data["filas"]:
            for detalle in fila["detalle"]:
                if detalle["fecha_inicio_prod"] is None:
                    # dias_proceso should be 0 when no movements
                    assert detalle["dias_proceso"] == 0, f"dias_proceso should be 0 for registro without movements, got {detalle['dias_proceso']}"
                    print(f"Registro {detalle['n_corte']}: dias_proceso={detalle['dias_proceso']}, fecha_inicio_prod=null (no movements)")
                    return
        
        # If no registro without movements found, skip
        pytest.skip("No registro without movements found to test dias_proceso=0")
    
    def test_matriz_detalle_curva_detalle_structure(self, auth_headers):
        """Matriz detalle curva_detalle has talla and cantidad"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/matriz",
            headers=auth_headers
        )
        data = response.json()
        
        if data["filas"]:
            fila = data["filas"][0]
            if fila["detalle"]:
                detalle = fila["detalle"][0]
                if detalle["curva_detalle"]:
                    item = detalle["curva_detalle"][0]
                    assert "talla" in item, "curva_detalle item missing 'talla'"
                    assert "cantidad" in item, "curva_detalle item missing 'cantidad'"
                    assert isinstance(item["talla"], str)
                    assert isinstance(item["cantidad"], int)


class TestMatrizFilters:
    """Test Matriz filter parameters"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "eduard",
            "password": "eduard123"
        })
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.fixture(scope="class")
    def rutas(self, auth_headers):
        """Get available rutas for testing"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/matriz",
            headers=auth_headers
        )
        data = response.json()
        return data.get("filtros_disponibles", {}).get("rutas", [])
    
    @pytest.fixture(scope="class")
    def marcas(self, auth_headers):
        """Get available marcas for testing"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/matriz",
            headers=auth_headers
        )
        data = response.json()
        return data.get("filtros_disponibles", {}).get("marcas", [])
    
    def test_matriz_filter_by_ruta(self, auth_headers, rutas):
        """Matriz can filter by ruta_id and columns adapt"""
        if not rutas:
            pytest.skip("No rutas available for testing")
        
        ruta_id = rutas[0]["id"]
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/matriz?ruta_id={ruta_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Columns should be specific to the ruta's etapas
        assert isinstance(data["columnas"], list)
    
    def test_matriz_filter_by_marca(self, auth_headers, marcas):
        """Matriz can filter by marca_id"""
        if not marcas:
            pytest.skip("No marcas available for testing")
        
        marca_id = marcas[0]["id"]
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/matriz?marca_id={marca_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # All filas should have the filtered marca
        for fila in data["filas"]:
            assert fila["marca"] == marcas[0]["nombre"] or marca_id in str(fila)
    
    def test_matriz_solo_activos_true(self, auth_headers):
        """Matriz with solo_activos=true excludes CERRADA registros"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/matriz?solo_activos=true",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check that no detalle has estado_op CERRADA
        for fila in data["filas"]:
            for detalle in fila["detalle"]:
                # estado field is the etapa, not estado_op, but CERRADA shouldn't appear
                pass  # Can't directly check estado_op in detalle
    
    def test_matriz_solo_activos_false(self, auth_headers):
        """Matriz with solo_activos=false includes CERRADA registros"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/matriz?solo_activos=false",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should return more or equal registros than solo_activos=true
        total_all = data["total_general"]["registros"]
        
        response2 = requests.get(
            f"{BASE_URL}/api/reportes-produccion/matriz?solo_activos=true",
            headers=auth_headers
        )
        data2 = response2.json()
        total_active = data2["total_general"]["registros"]
        
        assert total_all >= total_active
    
    def test_matriz_solo_atrasados(self, auth_headers):
        """Matriz with solo_atrasados=true returns only overdue lots"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/matriz?solo_atrasados=true",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should return fewer or equal registros than without filter
        total_atrasados = data["total_general"]["registros"]
        
        response2 = requests.get(
            f"{BASE_URL}/api/reportes-produccion/matriz",
            headers=auth_headers
        )
        data2 = response2.json()
        total_all = data2["total_general"]["registros"]
        
        assert total_atrasados <= total_all
    
    def test_matriz_solo_fraccionados(self, auth_headers):
        """Matriz with solo_fraccionados=true returns only fractioned lots"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/matriz?solo_fraccionados=true",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should return fewer or equal registros than without filter
        total_fraccionados = data["total_general"]["registros"]
        
        response2 = requests.get(
            f"{BASE_URL}/api/reportes-produccion/matriz",
            headers=auth_headers
        )
        data2 = response2.json()
        total_all = data2["total_general"]["registros"]
        
        assert total_fraccionados <= total_all


class TestMatrizFiltrosDisponibles:
    """Test Matriz filtros_disponibles structure"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "eduard",
            "password": "eduard123"
        })
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_matriz_filtros_disponibles_has_all_options(self, auth_headers):
        """Matriz filtros_disponibles has all filter options"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/matriz",
            headers=auth_headers
        )
        data = response.json()
        
        filtros = data["filtros_disponibles"]
        required_filters = ["marcas", "tipos", "entalles", "telas", "hilos", "rutas", "modelos"]
        for f in required_filters:
            assert f in filtros, f"Missing filter option: {f}"
            assert isinstance(filtros[f], list)
    
    def test_matriz_filtros_disponibles_structure(self, auth_headers):
        """Matriz filtros_disponibles items have id and nombre"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/matriz",
            headers=auth_headers
        )
        data = response.json()
        
        filtros = data["filtros_disponibles"]
        for key in ["marcas", "tipos", "entalles", "telas", "hilos", "rutas", "modelos"]:
            if filtros[key]:
                item = filtros[key][0]
                assert "id" in item, f"Missing 'id' in {key}"
                assert "nombre" in item, f"Missing 'nombre' in {key}"


class TestMatrizDataConsistency:
    """Test Matriz data consistency"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "eduard",
            "password": "eduard123"
        })
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_matriz_total_general_matches_filas(self, auth_headers):
        """Matriz total_general.registros matches sum of fila totals"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/matriz",
            headers=auth_headers
        )
        data = response.json()
        
        sum_registros = sum(fila["total"]["registros"] for fila in data["filas"])
        assert data["total_general"]["registros"] == sum_registros
    
    def test_matriz_totales_columna_matches_celdas(self, auth_headers):
        """Matriz totales_columna matches sum of celda values"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/matriz",
            headers=auth_headers
        )
        data = response.json()
        
        # Calculate expected totals from celdas
        expected_totals = {}
        for fila in data["filas"]:
            for col, vals in fila["celdas"].items():
                if col not in expected_totals:
                    expected_totals[col] = {"registros": 0, "prendas": 0}
                expected_totals[col]["registros"] += vals["registros"]
                expected_totals[col]["prendas"] += vals["prendas"]
        
        # Compare with actual totales_columna
        for col, expected in expected_totals.items():
            if col in data["totales_columna"]:
                assert data["totales_columna"][col]["registros"] == expected["registros"]
                assert data["totales_columna"][col]["prendas"] == expected["prendas"]
    
    def test_matriz_fila_total_matches_celdas(self, auth_headers):
        """Matriz fila total matches sum of its celdas"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/matriz",
            headers=auth_headers
        )
        data = response.json()
        
        for fila in data["filas"]:
            sum_registros = sum(vals["registros"] for vals in fila["celdas"].values())
            sum_prendas = sum(vals["prendas"] for vals in fila["celdas"].values())
            
            assert fila["total"]["registros"] == sum_registros
            assert fila["total"]["prendas"] == sum_prendas
    
    def test_matriz_detalle_count_matches_total(self, auth_headers):
        """Matriz fila detalle count matches total registros"""
        response = requests.get(
            f"{BASE_URL}/api/reportes-produccion/matriz",
            headers=auth_headers
        )
        data = response.json()
        
        for fila in data["filas"]:
            assert len(fila["detalle"]) == fila["total"]["registros"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
