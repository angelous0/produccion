"""
Test suite for Backup and Export functionality
Tests: backup/info, backup/create, export/{tabla}
"""
import pytest
import requests
import os
import json

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://textiladmin.preview.emergentagent.com').rstrip('/')

class TestBackupExport:
    """Tests for backup and export endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Login and get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "eduard",
            "password": "eduard123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    # ==================== BACKUP TESTS ====================
    
    def test_backup_info_returns_table_list(self):
        """GET /api/backup/info - Returns list of tables with counts"""
        response = requests.get(f"{BASE_URL}/api/backup/info", headers=self.headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "tables" in data
        assert isinstance(data["tables"], list)
        assert len(data["tables"]) > 0
        
        # Verify each table has name and count
        for table in data["tables"]:
            assert "name" in table
            assert "count" in table
            assert table["name"].startswith("prod_")
    
    def test_backup_info_requires_auth(self):
        """GET /api/backup/info - Returns 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/backup/info")
        assert response.status_code == 401
    
    def test_backup_create_downloads_json(self):
        """GET /api/backup/create - Downloads JSON backup file"""
        response = requests.get(f"{BASE_URL}/api/backup/create", headers=self.headers)
        
        assert response.status_code == 200
        assert "application/json" in response.headers.get("Content-Type", "")
        assert "attachment" in response.headers.get("Content-Disposition", "")
        
        # Verify JSON structure
        data = response.json()
        assert "version" in data
        assert "created_at" in data
        assert "created_by" in data
        assert "tables" in data
        assert data["created_by"] == "eduard"
        
        # Verify tables are included
        assert "prod_marcas" in data["tables"]
        assert "prod_usuarios" in data["tables"]
    
    def test_backup_create_requires_admin(self):
        """GET /api/backup/create - Requires admin role"""
        # Test without auth
        response = requests.get(f"{BASE_URL}/api/backup/create")
        assert response.status_code == 401
    
    # ==================== EXPORT TESTS ====================
    
    def test_export_registros_csv(self):
        """GET /api/export/registros - Exports registros to CSV"""
        response = requests.get(f"{BASE_URL}/api/export/registros", headers=self.headers)
        
        assert response.status_code == 200
        assert "text/csv" in response.headers.get("Content-Type", "")
        assert "attachment" in response.headers.get("Content-Disposition", "")
        
        # Verify CSV content
        content = response.text
        assert "N° Corte" in content
        assert "Fecha" in content
        assert "Estado" in content
    
    def test_export_inventario_csv(self):
        """GET /api/export/inventario - Exports inventario to CSV"""
        response = requests.get(f"{BASE_URL}/api/export/inventario", headers=self.headers)
        
        assert response.status_code == 200
        assert "text/csv" in response.headers.get("Content-Type", "")
        
        # Verify CSV content
        content = response.text
        assert "Código" in content
        assert "Nombre" in content
        assert "Stock Actual" in content
    
    def test_export_productividad_csv(self):
        """GET /api/export/productividad - Exports productividad to CSV"""
        response = requests.get(f"{BASE_URL}/api/export/productividad", headers=self.headers)
        
        assert response.status_code == 200
        assert "text/csv" in response.headers.get("Content-Type", "")
        
        content = response.text
        assert "Persona" in content
        assert "Servicio" in content
    
    def test_export_personas_csv(self):
        """GET /api/export/personas - Exports personas to CSV"""
        response = requests.get(f"{BASE_URL}/api/export/personas", headers=self.headers)
        
        assert response.status_code == 200
        assert "text/csv" in response.headers.get("Content-Type", "")
        
        content = response.text
        assert "Nombre" in content
        assert "Teléfono" in content
    
    def test_export_modelos_csv(self):
        """GET /api/export/modelos - Exports modelos to CSV"""
        response = requests.get(f"{BASE_URL}/api/export/modelos", headers=self.headers)
        
        assert response.status_code == 200
        assert "text/csv" in response.headers.get("Content-Type", "")
        
        content = response.text
        assert "Nombre" in content
        assert "Marca" in content
    
    def test_export_invalid_table_returns_400(self):
        """GET /api/export/{invalid} - Returns 400 for invalid table"""
        response = requests.get(f"{BASE_URL}/api/export/invalid_table", headers=self.headers)
        assert response.status_code == 400
    
    def test_export_requires_auth(self):
        """GET /api/export/registros - Returns 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/export/registros")
        assert response.status_code == 401


class TestPermissionsHook:
    """Tests for permissions structure endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Login and get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "eduard",
            "password": "eduard123"
        })
        assert response.status_code == 200
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_permisos_estructura_returns_categories(self):
        """GET /api/permisos/estructura - Returns permission categories"""
        response = requests.get(f"{BASE_URL}/api/permisos/estructura", headers=self.headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "categorias" in data
        assert len(data["categorias"]) > 0
        
        # Verify structure
        for cat in data["categorias"]:
            assert "nombre" in cat
            assert "tablas" in cat
            for tabla in cat["tablas"]:
                assert "key" in tabla
                assert "nombre" in tabla
                assert "acciones" in tabla


class TestActivityHistory:
    """Tests for activity history endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Login and get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "eduard",
            "password": "eduard123"
        })
        assert response.status_code == 200
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_actividad_returns_history(self):
        """GET /api/actividad - Returns activity history"""
        response = requests.get(f"{BASE_URL}/api/actividad", headers=self.headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "total" in data
        assert "items" in data
        assert isinstance(data["items"], list)
    
    def test_actividad_tipos_returns_action_types(self):
        """GET /api/actividad/tipos - Returns action types"""
        response = requests.get(f"{BASE_URL}/api/actividad/tipos", headers=self.headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) > 0
        
        # Verify structure
        for tipo in data:
            assert "value" in tipo
            assert "label" in tipo


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
