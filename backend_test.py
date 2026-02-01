import requests
import sys
import json
from datetime import datetime

class TextileAPITester:
    def __init__(self, base_url="https://textiladmin.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.auth_token = None
        self.created_items = {
            'marcas': [],
            'tipos': [],
            'entalles': [],
            'telas': [],
            'hilos': [],
            'modelos': [],
            'registros': []
        }

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        default_headers = {'Content-Type': 'application/json'}
        
        if headers:
            default_headers.update(headers)
        
        # Add auth token if available
        if self.auth_token:
            default_headers['Authorization'] = f'Bearer {self.auth_token}'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=default_headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=default_headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=default_headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=default_headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return True, response.json() if response.text else {}
                except:
                    return True, response
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                if response.text:
                    print(f"   Response: {response.text[:200]}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test root API endpoint"""
        return self.run_test("Root API", "GET", "", 200)

    def test_stats_endpoint(self):
        """Test stats endpoint"""
        return self.run_test("Stats", "GET", "stats", 200)

    def test_estados_endpoint(self):
        """Test estados endpoint"""
        return self.run_test("Estados", "GET", "estados", 200)

    def test_marcas_crud(self):
        """Test Marcas CRUD operations"""
        print("\n📋 Testing Marcas CRUD...")
        
        # Create
        marca_data = {"nombre": f"Marca Test {datetime.now().strftime('%H%M%S')}"}
        success, response = self.run_test("Create Marca", "POST", "marcas", 200, marca_data)
        if not success:
            return False
        marca_id = response.get('id')
        if marca_id:
            self.created_items['marcas'].append(marca_id)

        # Read all
        success, _ = self.run_test("Get All Marcas", "GET", "marcas", 200)
        if not success:
            return False

        # Update
        if marca_id:
            update_data = {"nombre": f"Marca Updated {datetime.now().strftime('%H%M%S')}"}
            success, _ = self.run_test("Update Marca", "PUT", f"marcas/{marca_id}", 200, update_data)
            if not success:
                return False

        # Delete
        if marca_id:
            success, _ = self.run_test("Delete Marca", "DELETE", f"marcas/{marca_id}", 200)
            if success:
                self.created_items['marcas'].remove(marca_id)
            return success

        return True

    def test_tipos_crud(self):
        """Test Tipos CRUD operations"""
        print("\n📋 Testing Tipos CRUD...")
        
        tipo_data = {"nombre": f"Tipo Test {datetime.now().strftime('%H%M%S')}"}
        success, response = self.run_test("Create Tipo", "POST", "tipos", 200, tipo_data)
        if not success:
            return False
        tipo_id = response.get('id')
        if tipo_id:
            self.created_items['tipos'].append(tipo_id)

        success, _ = self.run_test("Get All Tipos", "GET", "tipos", 200)
        if not success:
            return False

        if tipo_id:
            update_data = {"nombre": f"Tipo Updated {datetime.now().strftime('%H%M%S')}"}
            success, _ = self.run_test("Update Tipo", "PUT", f"tipos/{tipo_id}", 200, update_data)
            if not success:
                return False

            success, _ = self.run_test("Delete Tipo", "DELETE", f"tipos/{tipo_id}", 200)
            if success:
                self.created_items['tipos'].remove(tipo_id)
            return success

        return True

    def test_entalles_crud(self):
        """Test Entalles CRUD operations"""
        print("\n📋 Testing Entalles CRUD...")
        
        entalle_data = {"nombre": f"Entalle Test {datetime.now().strftime('%H%M%S')}"}
        success, response = self.run_test("Create Entalle", "POST", "entalles", 200, entalle_data)
        if not success:
            return False
        entalle_id = response.get('id')
        if entalle_id:
            self.created_items['entalles'].append(entalle_id)

        success, _ = self.run_test("Get All Entalles", "GET", "entalles", 200)
        if not success:
            return False

        if entalle_id:
            update_data = {"nombre": f"Entalle Updated {datetime.now().strftime('%H%M%S')}"}
            success, _ = self.run_test("Update Entalle", "PUT", f"entalles/{entalle_id}", 200, update_data)
            if not success:
                return False

            success, _ = self.run_test("Delete Entalle", "DELETE", f"entalles/{entalle_id}", 200)
            if success:
                self.created_items['entalles'].remove(entalle_id)
            return success

        return True

    def test_telas_crud(self):
        """Test Telas CRUD operations"""
        print("\n📋 Testing Telas CRUD...")
        
        tela_data = {"nombre": f"Tela Test {datetime.now().strftime('%H%M%S')}"}
        success, response = self.run_test("Create Tela", "POST", "telas", 200, tela_data)
        if not success:
            return False
        tela_id = response.get('id')
        if tela_id:
            self.created_items['telas'].append(tela_id)

        success, _ = self.run_test("Get All Telas", "GET", "telas", 200)
        if not success:
            return False

        if tela_id:
            update_data = {"nombre": f"Tela Updated {datetime.now().strftime('%H%M%S')}"}
            success, _ = self.run_test("Update Tela", "PUT", f"telas/{tela_id}", 200, update_data)
            if not success:
                return False

            success, _ = self.run_test("Delete Tela", "DELETE", f"telas/{tela_id}", 200)
            if success:
                self.created_items['telas'].remove(tela_id)
            return success

        return True

    def test_hilos_crud(self):
        """Test Hilos CRUD operations"""
        print("\n📋 Testing Hilos CRUD...")
        
        hilo_data = {"nombre": f"Hilo Test {datetime.now().strftime('%H%M%S')}"}
        success, response = self.run_test("Create Hilo", "POST", "hilos", 200, hilo_data)
        if not success:
            return False
        hilo_id = response.get('id')
        if hilo_id:
            self.created_items['hilos'].append(hilo_id)

        success, _ = self.run_test("Get All Hilos", "GET", "hilos", 200)
        if not success:
            return False

        if hilo_id:
            update_data = {"nombre": f"Hilo Updated {datetime.now().strftime('%H%M%S')}"}
            success, _ = self.run_test("Update Hilo", "PUT", f"hilos/{hilo_id}", 200, update_data)
            if not success:
                return False

            success, _ = self.run_test("Delete Hilo", "DELETE", f"hilos/{hilo_id}", 200)
            if success:
                self.created_items['hilos'].remove(hilo_id)
            return success

        return True

    def test_modelos_crud(self):
        """Test Modelos CRUD operations with relations"""
        print("\n📋 Testing Modelos CRUD...")
        
        # First create required related items
        marca_data = {"nombre": f"Marca for Model {datetime.now().strftime('%H%M%S')}"}
        success, marca_response = self.run_test("Create Marca for Model", "POST", "marcas", 200, marca_data)
        if not success:
            return False
        marca_id = marca_response.get('id')
        self.created_items['marcas'].append(marca_id)

        tipo_data = {"nombre": f"Tipo for Model {datetime.now().strftime('%H%M%S')}"}
        success, tipo_response = self.run_test("Create Tipo for Model", "POST", "tipos", 200, tipo_data)
        if not success:
            return False
        tipo_id = tipo_response.get('id')
        self.created_items['tipos'].append(tipo_id)

        entalle_data = {"nombre": f"Entalle for Model {datetime.now().strftime('%H%M%S')}"}
        success, entalle_response = self.run_test("Create Entalle for Model", "POST", "entalles", 200, entalle_data)
        if not success:
            return False
        entalle_id = entalle_response.get('id')
        self.created_items['entalles'].append(entalle_id)

        tela_data = {"nombre": f"Tela for Model {datetime.now().strftime('%H%M%S')}"}
        success, tela_response = self.run_test("Create Tela for Model", "POST", "telas", 200, tela_data)
        if not success:
            return False
        tela_id = tela_response.get('id')
        self.created_items['telas'].append(tela_id)

        hilo_data = {"nombre": f"Hilo for Model {datetime.now().strftime('%H%M%S')}"}
        success, hilo_response = self.run_test("Create Hilo for Model", "POST", "hilos", 200, hilo_data)
        if not success:
            return False
        hilo_id = hilo_response.get('id')
        self.created_items['hilos'].append(hilo_id)

        # Now create modelo
        modelo_data = {
            "nombre": f"Modelo Test {datetime.now().strftime('%H%M%S')}",
            "marca_id": marca_id,
            "tipo_id": tipo_id,
            "entalle_id": entalle_id,
            "tela_id": tela_id,
            "hilo_id": hilo_id
        }
        success, response = self.run_test("Create Modelo", "POST", "modelos", 200, modelo_data)
        if not success:
            return False
        modelo_id = response.get('id')
        if modelo_id:
            self.created_items['modelos'].append(modelo_id)

        success, _ = self.run_test("Get All Modelos", "GET", "modelos", 200)
        if not success:
            return False

        if modelo_id:
            update_data = {
                "nombre": f"Modelo Updated {datetime.now().strftime('%H%M%S')}",
                "marca_id": marca_id,
                "tipo_id": tipo_id,
                "entalle_id": entalle_id,
                "tela_id": tela_id,
                "hilo_id": hilo_id
            }
            success, _ = self.run_test("Update Modelo", "PUT", f"modelos/{modelo_id}", 200, update_data)
            if not success:
                return False

            success, _ = self.run_test("Delete Modelo", "DELETE", f"modelos/{modelo_id}", 200)
            if success:
                self.created_items['modelos'].remove(modelo_id)

        return True

    def test_tallas_catalogo_crud(self):
        """Test Tallas Catalogo CRUD operations"""
        print("\n📋 Testing Tallas Catalogo CRUD...")
        
        # Create
        talla_data = {"nombre": f"Talla Test {datetime.now().strftime('%H%M%S')}", "orden": 99}
        success, response = self.run_test("Create Talla Catalogo", "POST", "tallas-catalogo", 200, talla_data)
        if not success:
            return False
        talla_id = response.get('id')

        # Read all
        success, _ = self.run_test("Get All Tallas Catalogo", "GET", "tallas-catalogo", 200)
        if not success:
            return False

        # Update
        if talla_id:
            update_data = {"nombre": f"Talla Updated {datetime.now().strftime('%H%M%S')}", "orden": 100}
            success, _ = self.run_test("Update Talla Catalogo", "PUT", f"tallas-catalogo/{talla_id}", 200, update_data)
            if not success:
                return False

        # Delete
        if talla_id:
            success, _ = self.run_test("Delete Talla Catalogo", "DELETE", f"tallas-catalogo/{talla_id}", 200)
            return success

        return True

    def test_colores_catalogo_crud(self):
        """Test Colores Catalogo CRUD operations"""
        print("\n📋 Testing Colores Catalogo CRUD...")
        
        # Create
        color_data = {"nombre": f"Color Test {datetime.now().strftime('%H%M%S')}", "codigo_hex": "#FF5733"}
        success, response = self.run_test("Create Color Catalogo", "POST", "colores-catalogo", 200, color_data)
        if not success:
            return False
        color_id = response.get('id')

        # Read all
        success, _ = self.run_test("Get All Colores Catalogo", "GET", "colores-catalogo", 200)
        if not success:
            return False

        # Update
        if color_id:
            update_data = {"nombre": f"Color Updated {datetime.now().strftime('%H%M%S')}", "codigo_hex": "#33FF57"}
            success, _ = self.run_test("Update Color Catalogo", "PUT", f"colores-catalogo/{color_id}", 200, update_data)
            if not success:
                return False

        # Delete
        if color_id:
            success, _ = self.run_test("Delete Color Catalogo", "DELETE", f"colores-catalogo/{color_id}", 200)
            return success

        return True

    def test_registros_crud(self):
        """Test Registros CRUD operations with new tallas structure"""
        print("\n📋 Testing Registros CRUD...")
        
        # Create required items for modelo first
        marca_data = {"nombre": f"Marca for Registro {datetime.now().strftime('%H%M%S')}"}
        success, marca_response = self.run_test("Create Marca for Registro", "POST", "marcas", 200, marca_data)
        if not success:
            return False
        marca_id = marca_response.get('id')
        self.created_items['marcas'].append(marca_id)

        tipo_data = {"nombre": f"Tipo for Registro {datetime.now().strftime('%H%M%S')}"}
        success, tipo_response = self.run_test("Create Tipo for Registro", "POST", "tipos", 200, tipo_data)
        if not success:
            return False
        tipo_id = tipo_response.get('id')
        self.created_items['tipos'].append(tipo_id)

        entalle_data = {"nombre": f"Entalle for Registro {datetime.now().strftime('%H%M%S')}"}
        success, entalle_response = self.run_test("Create Entalle for Registro", "POST", "entalles", 200, entalle_data)
        if not success:
            return False
        entalle_id = entalle_response.get('id')
        self.created_items['entalles'].append(entalle_id)

        tela_data = {"nombre": f"Tela for Registro {datetime.now().strftime('%H%M%S')}"}
        success, tela_response = self.run_test("Create Tela for Registro", "POST", "telas", 200, tela_data)
        if not success:
            return False
        tela_id = tela_response.get('id')
        self.created_items['telas'].append(tela_id)

        hilo_data = {"nombre": f"Hilo for Registro {datetime.now().strftime('%H%M%S')}"}
        success, hilo_response = self.run_test("Create Hilo for Registro", "POST", "hilos", 200, hilo_data)
        if not success:
            return False
        hilo_id = hilo_response.get('id')
        self.created_items['hilos'].append(hilo_id)

        # Create modelo for registro
        modelo_data = {
            "nombre": f"Modelo for Registro {datetime.now().strftime('%H%M%S')}",
            "marca_id": marca_id,
            "tipo_id": tipo_id,
            "entalle_id": entalle_id,
            "tela_id": tela_id,
            "hilo_id": hilo_id
        }
        success, modelo_response = self.run_test("Create Modelo for Registro", "POST", "modelos", 200, modelo_data)
        if not success:
            return False
        modelo_id = modelo_response.get('id')
        self.created_items['modelos'].append(modelo_id)

        # Create tallas for testing
        talla1_data = {"nombre": "Test-S", "orden": 1}
        success, talla1_response = self.run_test("Create Test Talla 1", "POST", "tallas-catalogo", 200, talla1_data)
        if not success:
            return False
        talla1_id = talla1_response.get('id')

        talla2_data = {"nombre": "Test-M", "orden": 2}
        success, talla2_response = self.run_test("Create Test Talla 2", "POST", "tallas-catalogo", 200, talla2_data)
        if not success:
            return False
        talla2_id = talla2_response.get('id')

        # Create registro with new tallas structure
        registro_data = {
            "n_corte": f"CORTE-{datetime.now().strftime('%H%M%S')}",
            "modelo_id": modelo_id,
            "curva": "Curva Test",
            "estado": "Para Corte",
            "urgente": True,
            "tallas": [
                {"talla_id": talla1_id, "talla_nombre": "Test-S", "cantidad": 10},
                {"talla_id": talla2_id, "talla_nombre": "Test-M", "cantidad": 15}
            ],
            "distribucion_colores": []
        }
        success, response = self.run_test("Create Registro", "POST", "registros", 200, registro_data)
        if not success:
            return False
        registro_id = response.get('id')
        if registro_id:
            self.created_items['registros'].append(registro_id)

        success, _ = self.run_test("Get All Registros", "GET", "registros", 200)
        if not success:
            return False

        if registro_id:
            success, _ = self.run_test("Get Single Registro", "GET", f"registros/{registro_id}", 200)
            if not success:
                return False

            update_data = {
                "n_corte": f"CORTE-UPD-{datetime.now().strftime('%H%M%S')}",
                "modelo_id": modelo_id,
                "curva": "Curva Updated",
                "estado": "Corte",
                "urgente": False,
                "tallas": [
                    {"talla_id": talla1_id, "talla_nombre": "Test-S", "cantidad": 20}
                ],
                "distribucion_colores": []
            }
            success, _ = self.run_test("Update Registro", "PUT", f"registros/{registro_id}", 200, update_data)
            if not success:
                return False

            success, _ = self.run_test("Delete Registro", "DELETE", f"registros/{registro_id}", 200)
            if success:
                self.created_items['registros'].remove(registro_id)

        # Clean up test tallas
        self.run_test("Delete Test Talla 1", "DELETE", f"tallas-catalogo/{talla1_id}", 200)
        self.run_test("Delete Test Talla 2", "DELETE", f"tallas-catalogo/{talla2_id}", 200)

        return True

    def cleanup_created_items(self):
        """Clean up any remaining created items"""
        print("\n🧹 Cleaning up created items...")
        
        # Clean up in reverse order of dependencies
        for registro_id in self.created_items['registros']:
            self.run_test("Cleanup Registro", "DELETE", f"registros/{registro_id}", 200)
        
        for modelo_id in self.created_items['modelos']:
            self.run_test("Cleanup Modelo", "DELETE", f"modelos/{modelo_id}", 200)
        
        for marca_id in self.created_items['marcas']:
            self.run_test("Cleanup Marca", "DELETE", f"marcas/{marca_id}", 200)
        
        for tipo_id in self.created_items['tipos']:
            self.run_test("Cleanup Tipo", "DELETE", f"tipos/{tipo_id}", 200)
        
        for entalle_id in self.created_items['entalles']:
            self.run_test("Cleanup Entalle", "DELETE", f"entalles/{entalle_id}", 200)
        
        for tela_id in self.created_items['telas']:
            self.run_test("Cleanup Tela", "DELETE", f"telas/{tela_id}", 200)
        
        for hilo_id in self.created_items['hilos']:
            self.run_test("Cleanup Hilo", "DELETE", f"hilos/{hilo_id}", 200)

def main():
    print("🧪 Starting Textile Production API Tests...")
    tester = TextileAPITester()

    # Test basic endpoints
    if not tester.test_root_endpoint():
        print("❌ Root endpoint failed, stopping tests")
        return 1

    if not tester.test_stats_endpoint():
        print("❌ Stats endpoint failed")

    if not tester.test_estados_endpoint():
        print("❌ Estados endpoint failed")

    # Test CRUD operations
    test_results = []
    test_results.append(("Marcas CRUD", tester.test_marcas_crud()))
    test_results.append(("Tipos CRUD", tester.test_tipos_crud()))
    test_results.append(("Entalles CRUD", tester.test_entalles_crud()))
    test_results.append(("Telas CRUD", tester.test_telas_crud()))
    test_results.append(("Hilos CRUD", tester.test_hilos_crud()))
    test_results.append(("Tallas Catalogo CRUD", tester.test_tallas_catalogo_crud()))
    test_results.append(("Colores Catalogo CRUD", tester.test_colores_catalogo_crud()))
    test_results.append(("Modelos CRUD", tester.test_modelos_crud()))
    test_results.append(("Registros CRUD", tester.test_registros_crud()))

    # Cleanup
    tester.cleanup_created_items()

    # Print results
    print(f"\n📊 Final Results: {tester.tests_passed}/{tester.tests_run} tests passed")
    
    failed_tests = [name for name, result in test_results if not result]
    if failed_tests:
        print(f"❌ Failed test suites: {', '.join(failed_tests)}")
        return 1
    else:
        print("✅ All test suites passed!")
        return 0

if __name__ == "__main__":
    sys.exit(main())