"""
Test suite for Control Operativo en Producción Textil - Phase 2
Features tested:
1. fecha_entrega_final in registro (renamed from fecha_entrega_esperada)
2. fecha_esperada_movimiento and responsable_movimiento per movement
3. Visual alerts for movements
4. Estado operativo calculation based on overdue movements + paralizaciones
5. Incidencias with optional movimiento_id
6. Paralizaciones with optional movimiento_id
"""

import pytest
import requests
import os
from datetime import date, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestSetup:
    """Helper class for test setup"""
    
    @staticmethod
    def login():
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "eduard",
            "password": "eduard123"
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
    
    @staticmethod
    def get_headers(token):
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    @staticmethod
    def get_first_registro(token):
        """Get the first registro (corte 04)"""
        headers = TestSetup.get_headers(token)
        response = requests.get(f"{BASE_URL}/api/registros", headers=headers)
        if response.status_code == 200 and len(response.json()) > 0:
            return response.json()[0]
        return None


class TestFechaEntregaFinal:
    """Test PUT /api/registros/{id}/control - fecha_entrega_final"""
    
    def test_update_fecha_entrega_final(self):
        """Test updating fecha_entrega_final via control endpoint"""
        token = TestSetup.login()
        assert token is not None, "Login failed"
        
        headers = TestSetup.get_headers(token)
        registro = TestSetup.get_first_registro(token)
        assert registro is not None, "No registro found"
        
        # Set fecha_entrega_final to 7 days from now
        future_date = (date.today() + timedelta(days=7)).isoformat()
        
        response = requests.put(
            f"{BASE_URL}/api/registros/{registro['id']}/control",
            json={"fecha_entrega_final": future_date},
            headers=headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "estado_operativo" in data, "Response should include estado_operativo"
        print(f"✓ fecha_entrega_final updated successfully, estado_operativo: {data['estado_operativo']}")
    
    def test_fecha_entrega_final_null(self):
        """Test setting fecha_entrega_final to null"""
        token = TestSetup.login()
        assert token is not None, "Login failed"
        
        headers = TestSetup.get_headers(token)
        registro = TestSetup.get_first_registro(token)
        assert registro is not None, "No registro found"
        
        response = requests.put(
            f"{BASE_URL}/api/registros/{registro['id']}/control",
            json={"fecha_entrega_final": None},
            headers=headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ fecha_entrega_final can be set to null")
    
    def test_fecha_entrega_final_returned_in_registros(self):
        """Test that GET /api/registros returns fecha_entrega_final"""
        token = TestSetup.login()
        assert token is not None, "Login failed"
        
        headers = TestSetup.get_headers(token)
        
        # First, set a fecha_entrega_final
        registro = TestSetup.get_first_registro(token)
        future_date = (date.today() + timedelta(days=5)).isoformat()
        requests.put(
            f"{BASE_URL}/api/registros/{registro['id']}/control",
            json={"fecha_entrega_final": future_date},
            headers=headers
        )
        
        # Now get registros and verify field is returned
        response = requests.get(f"{BASE_URL}/api/registros", headers=headers)
        assert response.status_code == 200
        
        registros = response.json()
        assert len(registros) > 0, "No registros found"
        
        # Find our registro
        reg = next((r for r in registros if r['id'] == registro['id']), None)
        assert reg is not None, "Registro not found in list"
        assert "fecha_entrega_final" in reg, "fecha_entrega_final not in registro response"
        print(f"✓ fecha_entrega_final returned: {reg.get('fecha_entrega_final')}")


class TestMovimientosProduccion:
    """Test movimientos-produccion with new fields"""
    
    @pytest.fixture
    def setup_data(self):
        """Setup token, registro, servicio, persona for tests"""
        token = TestSetup.login()
        assert token is not None, "Login failed"
        
        headers = TestSetup.get_headers(token)
        registro = TestSetup.get_first_registro(token)
        assert registro is not None, "No registro found"
        
        # Get servicios
        servicios_res = requests.get(f"{BASE_URL}/api/servicios-produccion", headers=headers)
        servicios = servicios_res.json() if servicios_res.status_code == 200 else []
        
        # Get personas
        personas_res = requests.get(f"{BASE_URL}/api/personas-produccion?activo=true", headers=headers)
        personas = personas_res.json() if personas_res.status_code == 200 else []
        
        return {
            "token": token,
            "headers": headers,
            "registro": registro,
            "servicio": servicios[0] if servicios else None,
            "persona": personas[0] if personas else None
        }
    
    def test_create_movimiento_with_new_fields(self, setup_data):
        """Test creating movimiento with fecha_esperada_movimiento and responsable_movimiento"""
        headers = setup_data["headers"]
        registro = setup_data["registro"]
        servicio = setup_data["servicio"]
        persona = setup_data["persona"]
        
        if not servicio or not persona:
            pytest.skip("No servicio or persona available")
        
        fecha_esperada = (date.today() + timedelta(days=3)).isoformat()
        
        payload = {
            "registro_id": registro["id"],
            "servicio_id": servicio["id"],
            "persona_id": persona["id"],
            "cantidad_enviada": 50,
            "cantidad_recibida": 50,
            "tarifa_aplicada": 1.5,
            "fecha_inicio": date.today().isoformat(),
            "fecha_esperada_movimiento": fecha_esperada,
            "responsable_movimiento": "Juan Test",
            "observaciones": "Test movimiento v2"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/movimientos-produccion",
            json=payload,
            headers=headers
        )
        
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify returned data
        assert data.get("fecha_esperada_movimiento") == fecha_esperada, "fecha_esperada_movimiento mismatch"
        assert data.get("responsable_movimiento") == "Juan Test", "responsable_movimiento mismatch"
        
        # Cleanup - delete movimiento
        if data.get("id"):
            requests.delete(f"{BASE_URL}/api/movimientos-produccion/{data['id']}", headers=headers)
        
        print(f"✓ Movimiento created with fecha_esperada_movimiento={fecha_esperada}, responsable_movimiento=Juan Test")
    
    def test_update_movimiento_new_fields(self, setup_data):
        """Test updating movimiento with new fields"""
        headers = setup_data["headers"]
        registro = setup_data["registro"]
        servicio = setup_data["servicio"]
        persona = setup_data["persona"]
        
        if not servicio or not persona:
            pytest.skip("No servicio or persona available")
        
        # Create a movimiento first
        create_payload = {
            "registro_id": registro["id"],
            "servicio_id": servicio["id"],
            "persona_id": persona["id"],
            "cantidad_enviada": 30,
            "cantidad_recibida": 30,
            "tarifa_aplicada": 1.0,
            "fecha_inicio": date.today().isoformat(),
            "observaciones": "To update"
        }
        
        create_res = requests.post(
            f"{BASE_URL}/api/movimientos-produccion",
            json=create_payload,
            headers=headers
        )
        assert create_res.status_code in [200, 201], f"Create failed: {create_res.text}"
        mov_id = create_res.json().get("id")
        
        # Update with new fields
        nueva_fecha = (date.today() + timedelta(days=10)).isoformat()
        update_payload = {
            "registro_id": registro["id"],
            "servicio_id": servicio["id"],
            "persona_id": persona["id"],
            "cantidad_enviada": 30,
            "cantidad_recibida": 28,
            "tarifa_aplicada": 1.2,
            "fecha_inicio": date.today().isoformat(),
            "fecha_esperada_movimiento": nueva_fecha,
            "responsable_movimiento": "Maria Responsable",
            "observaciones": "Updated"
        }
        
        update_res = requests.put(
            f"{BASE_URL}/api/movimientos-produccion/{mov_id}",
            json=update_payload,
            headers=headers
        )
        
        assert update_res.status_code == 200, f"Update failed: {update_res.text}"
        updated = update_res.json()
        assert updated.get("fecha_esperada_movimiento") == nueva_fecha
        assert updated.get("responsable_movimiento") == "Maria Responsable"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/movimientos-produccion/{mov_id}", headers=headers)
        
        print(f"✓ Movimiento updated with new fecha_esperada_movimiento and responsable_movimiento")
    
    def test_get_movimientos_returns_new_fields(self, setup_data):
        """Test that GET /api/movimientos-produccion returns new fields"""
        headers = setup_data["headers"]
        registro = setup_data["registro"]
        servicio = setup_data["servicio"]
        persona = setup_data["persona"]
        
        if not servicio or not persona:
            pytest.skip("No servicio or persona available")
        
        # Create movimiento with new fields
        fecha_esperada = (date.today() + timedelta(days=5)).isoformat()
        create_payload = {
            "registro_id": registro["id"],
            "servicio_id": servicio["id"],
            "persona_id": persona["id"],
            "cantidad_enviada": 25,
            "cantidad_recibida": 25,
            "tarifa_aplicada": 2.0,
            "fecha_inicio": date.today().isoformat(),
            "fecha_esperada_movimiento": fecha_esperada,
            "responsable_movimiento": "Carlos GET Test",
            "observaciones": "GET test"
        }
        
        create_res = requests.post(
            f"{BASE_URL}/api/movimientos-produccion",
            json=create_payload,
            headers=headers
        )
        mov_id = create_res.json().get("id")
        
        # GET movimientos
        get_res = requests.get(
            f"{BASE_URL}/api/movimientos-produccion?registro_id={registro['id']}",
            headers=headers
        )
        
        assert get_res.status_code == 200
        movimientos = get_res.json()
        
        # Find our movimiento
        mov = next((m for m in movimientos if m.get("id") == mov_id), None)
        assert mov is not None, "Created movimiento not found in list"
        assert "fecha_esperada_movimiento" in mov, "fecha_esperada_movimiento not in response"
        assert "responsable_movimiento" in mov, "responsable_movimiento not in response"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/movimientos-produccion/{mov_id}", headers=headers)
        
        print(f"✓ GET /api/movimientos-produccion returns fecha_esperada_movimiento and responsable_movimiento")


class TestIncidenciasWithMovimiento:
    """Test incidencias with optional movimiento_id"""
    
    def test_create_incidencia_with_movimiento_id(self):
        """Test creating incidencia with optional movimiento_id"""
        token = TestSetup.login()
        assert token is not None, "Login failed"
        
        headers = TestSetup.get_headers(token)
        registro = TestSetup.get_first_registro(token)
        assert registro is not None, "No registro found"
        
        # Get movimientos for this registro
        mov_res = requests.get(
            f"{BASE_URL}/api/movimientos-produccion?registro_id={registro['id']}",
            headers=headers
        )
        movimientos = mov_res.json() if mov_res.status_code == 200 else []
        
        # Create incidencia without movimiento_id (should work)
        payload1 = {
            "registro_id": registro["id"],
            "tipo": "FALTA_MATERIAL",
            "comentario": "Test incidencia sin movimiento",
            "usuario": "test"
        }
        
        res1 = requests.post(f"{BASE_URL}/api/incidencias", json=payload1, headers=headers)
        assert res1.status_code in [200, 201], f"Create failed: {res1.text}"
        inc1 = res1.json()
        assert inc1.get("movimiento_id") is None or inc1.get("movimiento_id") == ""
        print("✓ Incidencia created without movimiento_id")
        
        # If there are movimientos, create incidencia with movimiento_id
        if movimientos:
            mov_id = movimientos[0]["id"]
            payload2 = {
                "registro_id": registro["id"],
                "movimiento_id": mov_id,
                "tipo": "RETRASO_TALLER",
                "comentario": "Test incidencia con movimiento",
                "usuario": "test"
            }
            
            res2 = requests.post(f"{BASE_URL}/api/incidencias", json=payload2, headers=headers)
            assert res2.status_code in [200, 201], f"Create with mov_id failed: {res2.text}"
            inc2 = res2.json()
            assert inc2.get("movimiento_id") == mov_id
            print(f"✓ Incidencia created with movimiento_id={mov_id}")
    
    def test_get_incidencias_enriched_movimiento_servicio(self):
        """Test that GET /api/incidencias returns movimiento_servicio enriched"""
        token = TestSetup.login()
        assert token is not None, "Login failed"
        
        headers = TestSetup.get_headers(token)
        registro = TestSetup.get_first_registro(token)
        
        # Get incidencias
        res = requests.get(f"{BASE_URL}/api/incidencias/{registro['id']}", headers=headers)
        assert res.status_code == 200
        
        incidencias = res.json()
        print(f"Found {len(incidencias)} incidencias for registro")
        
        # Check if any incidencia has movimiento_servicio
        for inc in incidencias:
            if inc.get("movimiento_id"):
                # Should have movimiento_servicio enriched
                assert "movimiento_servicio" in inc, "movimiento_servicio should be enriched"
                print(f"✓ Incidencia {inc['id'][:8]} has movimiento_servicio: {inc.get('movimiento_servicio')}")
                break
        else:
            print("✓ No incidencias with movimiento_id found, enrichment logic exists but not testable")


class TestParalizacionesWithMovimiento:
    """Test paralizaciones with optional movimiento_id"""
    
    def test_create_paralizacion_sets_estado_paralizada(self):
        """Test creating paralización sets estado_operativo to PARALIZADA"""
        token = TestSetup.login()
        assert token is not None, "Login failed"
        
        headers = TestSetup.get_headers(token)
        registro = TestSetup.get_first_registro(token)
        assert registro is not None, "No registro found"
        
        # Check if there's already an active paralizacion
        par_res = requests.get(f"{BASE_URL}/api/paralizaciones/{registro['id']}", headers=headers)
        paralizaciones = par_res.json() if par_res.status_code == 200 else []
        active_par = next((p for p in paralizaciones if p.get("activa")), None)
        
        if active_par:
            # Levantar existing paralizacion first
            requests.put(f"{BASE_URL}/api/paralizaciones/{active_par['id']}/levantar", headers=headers)
        
        # Create paralización
        payload = {
            "registro_id": registro["id"],
            "motivo": "FALTA_MATERIAL",
            "comentario": "Test paralización estado"
        }
        
        res = requests.post(f"{BASE_URL}/api/paralizaciones", json=payload, headers=headers)
        assert res.status_code in [200, 201], f"Create failed: {res.text}"
        par = res.json()
        par_id = par.get("id")
        
        # Verify estado_operativo is PARALIZADA
        reg_res = requests.get(f"{BASE_URL}/api/registros", headers=headers)
        registros = reg_res.json()
        reg = next((r for r in registros if r['id'] == registro['id']), None)
        
        assert reg.get("estado_operativo") == "PARALIZADA", f"Expected PARALIZADA, got {reg.get('estado_operativo')}"
        print("✓ Creating paralización sets estado_operativo to PARALIZADA")
        
        # Cleanup - levantar
        requests.put(f"{BASE_URL}/api/paralizaciones/{par_id}/levantar", headers=headers)
    
    def test_levantar_paralizacion_recalculates_estado(self):
        """Test lifting paralización recalculates estado_operativo"""
        token = TestSetup.login()
        assert token is not None, "Login failed"
        
        headers = TestSetup.get_headers(token)
        registro = TestSetup.get_first_registro(token)
        
        # Ensure no active paralizacion
        par_res = requests.get(f"{BASE_URL}/api/paralizaciones/{registro['id']}", headers=headers)
        paralizaciones = par_res.json() if par_res.status_code == 200 else []
        for p in paralizaciones:
            if p.get("activa"):
                requests.put(f"{BASE_URL}/api/paralizaciones/{p['id']}/levantar", headers=headers)
        
        # Create paralización
        payload = {
            "registro_id": registro["id"],
            "motivo": "TALLER",
            "comentario": "Test levantar"
        }
        res = requests.post(f"{BASE_URL}/api/paralizaciones", json=payload, headers=headers)
        par_id = res.json().get("id")
        
        # Levantar
        lev_res = requests.put(f"{BASE_URL}/api/paralizaciones/{par_id}/levantar", headers=headers)
        assert lev_res.status_code == 200, f"Levantar failed: {lev_res.text}"
        
        # Verify estado_operativo is recalculated (not PARALIZADA anymore)
        reg_res = requests.get(f"{BASE_URL}/api/registros", headers=headers)
        registros = reg_res.json()
        reg = next((r for r in registros if r['id'] == registro['id']), None)
        
        # Should be NORMAL or EN_RIESGO based on movimientos vencidos
        assert reg.get("estado_operativo") in ["NORMAL", "EN_RIESGO"], f"Unexpected estado: {reg.get('estado_operativo')}"
        print(f"✓ After levantar, estado_operativo recalculated to: {reg.get('estado_operativo')}")
    
    def test_create_paralizacion_with_movimiento_id(self):
        """Test creating paralización with optional movimiento_id"""
        token = TestSetup.login()
        assert token is not None, "Login failed"
        
        headers = TestSetup.get_headers(token)
        registro = TestSetup.get_first_registro(token)
        
        # Get movimientos
        mov_res = requests.get(
            f"{BASE_URL}/api/movimientos-produccion?registro_id={registro['id']}",
            headers=headers
        )
        movimientos = mov_res.json() if mov_res.status_code == 200 else []
        
        if not movimientos:
            # Create a movimiento first
            srv_res = requests.get(f"{BASE_URL}/api/servicios-produccion", headers=headers)
            per_res = requests.get(f"{BASE_URL}/api/personas-produccion?activo=true", headers=headers)
            servicios = srv_res.json() if srv_res.status_code == 200 else []
            personas = per_res.json() if per_res.status_code == 200 else []
            
            if servicios and personas:
                mov_payload = {
                    "registro_id": registro["id"],
                    "servicio_id": servicios[0]["id"],
                    "persona_id": personas[0]["id"],
                    "cantidad_enviada": 10,
                    "cantidad_recibida": 10,
                    "tarifa_aplicada": 1.0,
                    "fecha_inicio": date.today().isoformat()
                }
                mov_create = requests.post(f"{BASE_URL}/api/movimientos-produccion", json=mov_payload, headers=headers)
                if mov_create.status_code in [200, 201]:
                    movimientos = [mov_create.json()]
        
        if movimientos:
            mov_id = movimientos[0]["id"]
            
            # Clean existing paralizaciones for this movimiento
            par_res = requests.get(f"{BASE_URL}/api/paralizaciones/{registro['id']}", headers=headers)
            for p in par_res.json():
                if p.get("movimiento_id") == mov_id and p.get("activa"):
                    requests.put(f"{BASE_URL}/api/paralizaciones/{p['id']}/levantar", headers=headers)
            
            # Create paralización with movimiento_id
            payload = {
                "registro_id": registro["id"],
                "movimiento_id": mov_id,
                "motivo": "CALIDAD",
                "comentario": "Test con movimiento"
            }
            
            res = requests.post(f"{BASE_URL}/api/paralizaciones", json=payload, headers=headers)
            assert res.status_code in [200, 201], f"Create failed: {res.text}"
            par = res.json()
            assert par.get("movimiento_id") == mov_id
            print(f"✓ Paralización created with movimiento_id={mov_id}")
            
            # Cleanup
            requests.put(f"{BASE_URL}/api/paralizaciones/{par['id']}/levantar", headers=headers)
        else:
            print("✓ No movimientos available, skipping movimiento_id test")


class TestEstadoOperativoLogic:
    """Test estado_operativo calculation logic"""
    
    def test_estado_en_riesgo_with_overdue_movimiento(self):
        """Test estado is EN_RIESGO when movimiento has overdue fecha_esperada_movimiento"""
        token = TestSetup.login()
        assert token is not None, "Login failed"
        
        headers = TestSetup.get_headers(token)
        registro = TestSetup.get_first_registro(token)
        
        # Get servicios and personas
        srv_res = requests.get(f"{BASE_URL}/api/servicios-produccion", headers=headers)
        per_res = requests.get(f"{BASE_URL}/api/personas-produccion?activo=true", headers=headers)
        servicios = srv_res.json() if srv_res.status_code == 200 else []
        personas = per_res.json() if per_res.status_code == 200 else []
        
        if not servicios or not personas:
            pytest.skip("No servicios or personas available")
        
        # First, ensure no active paralizaciones
        par_res = requests.get(f"{BASE_URL}/api/paralizaciones/{registro['id']}", headers=headers)
        for p in par_res.json():
            if p.get("activa"):
                requests.put(f"{BASE_URL}/api/paralizaciones/{p['id']}/levantar", headers=headers)
        
        # Create movimiento with past fecha_esperada_movimiento
        past_date = (date.today() - timedelta(days=2)).isoformat()
        payload = {
            "registro_id": registro["id"],
            "servicio_id": servicios[0]["id"],
            "persona_id": personas[0]["id"],
            "cantidad_enviada": 20,
            "cantidad_recibida": 20,
            "tarifa_aplicada": 1.0,
            "fecha_inicio": (date.today() - timedelta(days=5)).isoformat(),
            "fecha_esperada_movimiento": past_date,
            "responsable_movimiento": "Test EN_RIESGO"
        }
        
        mov_res = requests.post(f"{BASE_URL}/api/movimientos-produccion", json=payload, headers=headers)
        mov_id = mov_res.json().get("id") if mov_res.status_code in [200, 201] else None
        
        # Trigger recalculation via control endpoint
        requests.put(
            f"{BASE_URL}/api/registros/{registro['id']}/control",
            json={"fecha_entrega_final": None},
            headers=headers
        )
        
        # Get registro and check estado_operativo
        reg_res = requests.get(f"{BASE_URL}/api/registros", headers=headers)
        registros = reg_res.json()
        reg = next((r for r in registros if r['id'] == registro['id']), None)
        
        # If registro is not in Almacén PT and has overdue movimiento, should be EN_RIESGO
        if reg.get("estado") != "Almacén PT":
            assert reg.get("estado_operativo") == "EN_RIESGO", f"Expected EN_RIESGO, got {reg.get('estado_operativo')}"
            print(f"✓ Estado is EN_RIESGO with overdue movimiento (fecha_esperada: {past_date})")
        else:
            print(f"✓ Registro is in Almacén PT, estado_operativo logic differs")
        
        # Cleanup
        if mov_id:
            requests.delete(f"{BASE_URL}/api/movimientos-produccion/{mov_id}", headers=headers)
    
    def test_registros_returns_all_expected_fields(self):
        """Test GET /api/registros returns all expected control fields"""
        token = TestSetup.login()
        assert token is not None, "Login failed"
        
        headers = TestSetup.get_headers(token)
        
        response = requests.get(f"{BASE_URL}/api/registros", headers=headers)
        assert response.status_code == 200
        
        registros = response.json()
        assert len(registros) > 0, "No registros found"
        
        # Check first registro has all expected fields
        reg = registros[0]
        expected_fields = [
            "estado_operativo",
            "fecha_entrega_final",
            "incidencias_abiertas",
            "paralizacion_activa"
        ]
        
        missing_fields = [f for f in expected_fields if f not in reg]
        assert len(missing_fields) == 0, f"Missing fields in registro response: {missing_fields}"
        
        print(f"✓ GET /api/registros returns all control fields:")
        print(f"  - estado_operativo: {reg.get('estado_operativo')}")
        print(f"  - fecha_entrega_final: {reg.get('fecha_entrega_final')}")
        print(f"  - incidencias_abiertas: {reg.get('incidencias_abiertas')}")
        print(f"  - paralizacion_activa: {reg.get('paralizacion_activa')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
