#!/usr/bin/env python3
"""
BOM Module Test Suite
Tests for the Bill of Materials (BOM) functionality including:
- Modelo ↔ Tallas relationships
- BOM lines (general and per-talla)
- Validations and error handling
"""

import requests
import sys
import json
from datetime import datetime

class BOMModuleTester:
    def __init__(self, base_url="https://textile-production-2.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.auth_token = None
        self.test_data = {
            'modelo_id': None,
            'talla_id': None,
            'inventario_id': None,
            'created_relations': [],
            'created_bom_lines': []
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
        print(f"\n🔍 Test {self.tests_run}: {name}...")
        
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
                print(f"✅ PASS - Status: {response.status_code}")
                try:
                    return True, response.json() if response.text else {}
                except:
                    return True, response
            else:
                print(f"❌ FAIL - Expected {expected_status}, got {response.status_code}")
                if response.text:
                    print(f"   Response: {response.text[:300]}")
                return False, {}

        except Exception as e:
            print(f"❌ FAIL - Error: {str(e)}")
            return False, {}

    def setup_authentication(self):
        """Test login with eduard/eduard123 credentials"""
        print("\n🔐 Setting up authentication...")
        login_data = {
            "username": "eduard",
            "password": "eduard123"
        }
        success, response = self.run_test("Admin Login", "POST", "auth/login", 200, login_data)
        if success and 'access_token' in response:
            self.auth_token = response['access_token']
            print(f"✅ Authentication successful")
            return True
        else:
            print(f"❌ Authentication failed")
            return False

    def setup_test_data(self):
        """Get existing modelo, talla, and inventario for testing"""
        print("\n📋 Setting up test data...")
        
        # Get existing modelo
        success, modelos_response = self.run_test("Get Existing Modelos", "GET", "modelos", 200)
        if not success or not modelos_response:
            print("❌ No modelos available for testing")
            return False
        
        self.test_data['modelo_id'] = modelos_response[0]['id']
        print(f"✅ Using modelo_id: {self.test_data['modelo_id']}")
        
        # Get existing tallas from catalog
        success, tallas_response = self.run_test("Get Tallas Catalogo", "GET", "tallas-catalogo", 200)
        if not success or not tallas_response:
            print("❌ No tallas available for testing")
            return False
        
        # Check which tallas are already associated with this modelo
        modelo_id = self.test_data['modelo_id']
        success, existing_tallas = self.run_test("Get Existing Modelo Tallas", "GET", f"modelos/{modelo_id}/tallas?activo=all", 200)
        
        existing_talla_ids = [t['talla_id'] for t in existing_tallas] if existing_tallas else []
        
        # Find a talla that's NOT already associated with this modelo
        available_talla = None
        for talla in tallas_response:
            if talla['id'] not in existing_talla_ids:
                available_talla = talla
                break
        
        if available_talla:
            self.test_data['talla_id'] = available_talla['id']
            print(f"✅ Using available talla_id: {self.test_data['talla_id']} ({available_talla['nombre']})")
        else:
            # If all tallas are used, we'll use the first one but modify our test strategy
            self.test_data['talla_id'] = tallas_response[0]['id']
            self.test_data['talla_already_exists'] = True
            print(f"⚠️  All tallas already associated, using: {self.test_data['talla_id']} (will test different scenarios)")
        
        # Get existing inventario items
        success, inventario_response = self.run_test("Get Inventario Items", "GET", "inventario", 200)
        if not success or not inventario_response:
            print("❌ No inventario items available for testing")
            return False
        
        # Check existing BOM lines to find available inventario
        success, existing_bom = self.run_test("Get Existing BOM Lines", "GET", f"modelos/{modelo_id}/bom?activo=all", 200)
        
        existing_inventario_ids = []
        if existing_bom:
            for bom_line in existing_bom:
                key = (bom_line['inventario_id'], bom_line.get('talla_id'))
                existing_inventario_ids.append(key)
        
        # Find an inventario item that doesn't have conflicts
        available_inventario = None
        for inv in inventario_response:
            # Check if this inventario + our talla combination already exists
            key = (inv['id'], self.test_data['talla_id'])
            general_key = (inv['id'], None)
            if key not in existing_inventario_ids and general_key not in existing_inventario_ids:
                available_inventario = inv
                break
        
        if available_inventario:
            self.test_data['inventario_id'] = available_inventario['id']
            print(f"✅ Using available inventario_id: {self.test_data['inventario_id']} ({available_inventario['nombre']})")
        else:
            # Use a different inventario item for testing
            if len(inventario_response) > 1:
                self.test_data['inventario_id'] = inventario_response[1]['id']
                print(f"✅ Using alternative inventario_id: {self.test_data['inventario_id']}")
            else:
                self.test_data['inventario_id'] = inventario_response[0]['id']
                self.test_data['inventario_conflicts'] = True
                print(f"⚠️  Using inventario with potential conflicts: {self.test_data['inventario_id']}")
        
        return True

    def test_modelo_tallas_relationships(self):
        """Test MODELO↔TALLAS relationship operations"""
        print("\n📋 Testing MODELO↔TALLAS relationships...")
        
        modelo_id = self.test_data['modelo_id']
        talla_id = self.test_data['talla_id']
        
        # Check if talla already exists
        if self.test_data.get('talla_already_exists'):
            print("⚠️  Talla already exists, testing different scenarios...")
            
            # Test getting existing tallas
            success, active_tallas = self.run_test(
                "GET existing active tallas", 
                "GET", 
                f"modelos/{modelo_id}/tallas?activo=true", 
                200
            )
            if not success:
                return False
            
            print(f"✅ Found {len(active_tallas)} existing active talla(s)")
            
            # Test duplicate validation with existing talla
            talla_data = {"talla_id": talla_id, "orden": 1}
            success, _ = self.run_test(
                "POST duplicate existing talla (should fail 400)", 
                "POST", 
                f"modelos/{modelo_id}/tallas", 
                400, 
                talla_data
            )
            if not success:
                print("❌ Duplicate talla validation failed")
                return False
            
            # Find an existing relation to test update/delete
            if active_tallas:
                existing_rel = active_tallas[0]
                rel_id = existing_rel['id']
                
                # Test update existing relation
                update_data = {"orden": existing_rel['orden'] + 1}
                success, _ = self.run_test(
                    "PUT update existing modelo-talla", 
                    "PUT", 
                    f"modelos/{modelo_id}/tallas/{rel_id}", 
                    200, 
                    update_data
                )
                if not success:
                    return False
                
                print("✅ Updated existing modelo-talla relationship")
            
        else:
            # Test normal flow with new talla
            # Test 4: POST modelo-talla relationship
            talla_data = {"talla_id": talla_id, "orden": 1}
            success, talla_rel_response = self.run_test(
                "POST new modelo-talla relationship", 
                "POST", 
                f"modelos/{modelo_id}/tallas", 
                200, 
                talla_data
            )
            if not success:
                return False
            
            rel_id = talla_rel_response.get('id')
            if rel_id:
                self.test_data['created_relations'].append(rel_id)
            print(f"✅ Created modelo-talla relationship with ID: {rel_id}")
            
            # Test 5: POST duplicate talla should fail with 400
            success, _ = self.run_test(
                "POST duplicate talla (should fail 400)", 
                "POST", 
                f"modelos/{modelo_id}/tallas", 
                400, 
                talla_data
            )
            if not success:
                print("❌ Duplicate talla validation failed")
                return False
            
            # Test 6: GET active tallas for modelo
            success, active_tallas = self.run_test(
                "GET active tallas for modelo", 
                "GET", 
                f"modelos/{modelo_id}/tallas?activo=true", 
                200
            )
            if not success or not active_tallas:
                return False
            
            print(f"✅ Found {len(active_tallas)} active talla(s)")
            
            # Test 7: DELETE (soft delete) modelo-talla relationship
            if rel_id:
                success, _ = self.run_test(
                    "DELETE modelo-talla relationship", 
                    "DELETE", 
                    f"modelos/{modelo_id}/tallas/{rel_id}", 
                    200
                )
                if not success:
                    return False
            
            # Test 8: GET active tallas should not include deactivated one
            success, active_tallas_after = self.run_test(
                "GET active tallas after delete", 
                "GET", 
                f"modelos/{modelo_id}/tallas?activo=true", 
                200
            )
            if not success:
                return False
            
            if len(active_tallas_after) >= len(active_tallas):
                print("❌ Talla was not properly deactivated")
                return False
            
            # Test 9: PUT to reactivate and validate no duplicate
            if rel_id:
                reactivate_data = {"activo": True, "orden": 2}
                success, _ = self.run_test(
                    "PUT reactivate modelo-talla", 
                    "PUT", 
                    f"modelos/{modelo_id}/tallas/{rel_id}", 
                    200, 
                    reactivate_data
                )
                if not success:
                    return False
        
        print("✅ MODELO↔TALLAS relationship tests completed successfully")
        return True

    def test_bom_operations(self):
        """Test BOM line operations"""
        print("\n🔧 Testing BOM operations...")
        
        modelo_id = self.test_data['modelo_id']
        talla_id = self.test_data['talla_id']
        inventario_id = self.test_data['inventario_id']
        
        # Check for conflicts first
        if self.test_data.get('inventario_conflicts'):
            print("⚠️  Inventario conflicts detected, testing validation scenarios...")
            
            # Test duplicate validation
            bom_general_data = {
                "inventario_id": inventario_id,
                "talla_id": None,
                "cantidad_base": 2.5,
                "merma_pct": 5.0,
                "orden": 1,
                "activo": True,
                "notas": "Test línea general"
            }
            success, _ = self.run_test(
                "POST duplicate general BOM (should fail 400)", 
                "POST", 
                f"modelos/{modelo_id}/bom", 
                400, 
                bom_general_data
            )
            if not success:
                print("❌ Expected duplicate validation to fail with 400")
                return False
            
            print("✅ Duplicate BOM validation working correctly")
            
        else:
            # Test normal flow with available inventario
            # Test 10: POST BOM line GENERAL (talla_id null)
            bom_general_data = {
                "inventario_id": inventario_id,
                "talla_id": None,
                "cantidad_base": 2.5,
                "merma_pct": 5.0,
                "orden": 1,
                "activo": True,
                "notas": "Línea general de BOM"
            }
            success, bom_general_response = self.run_test(
                "POST general BOM line (talla_id null)", 
                "POST", 
                f"modelos/{modelo_id}/bom", 
                200, 
                bom_general_data
            )
            if not success:
                return False
            
            bom_general_id = bom_general_response.get('id')
            if bom_general_id:
                self.test_data['created_bom_lines'].append(bom_general_id)
            
            # Test 11: POST duplicate exact active BOM line should fail
            success, _ = self.run_test(
                "POST duplicate general BOM (should fail 400)", 
                "POST", 
                f"modelos/{modelo_id}/bom", 
                400, 
                bom_general_data
            )
            if not success:
                print("❌ Duplicate BOM validation failed")
                return False
            
            # Test 12: POST BOM line POR TALLA with valid talla_id
            bom_talla_data = {
                "inventario_id": inventario_id,
                "talla_id": talla_id,
                "cantidad_base": 1.8,
                "merma_pct": 3.0,
                "orden": 2,
                "activo": True,
                "notas": "Línea por talla específica"
            }
            success, bom_talla_response = self.run_test(
                "POST talla-specific BOM line", 
                "POST", 
                f"modelos/{modelo_id}/bom", 
                200, 
                bom_talla_data
            )
            if not success:
                return False
            
            bom_talla_id = bom_talla_response.get('id')
            if bom_talla_id:
                self.test_data['created_bom_lines'].append(bom_talla_id)
        
        # Test 13: POST BOM with talla_id that doesn't belong to modelo should fail
        # Get all tallas and find one not associated with this modelo
        success, all_tallas = self.run_test("Get all tallas for invalid test", "GET", "tallas-catalogo", 200)
        success2, modelo_tallas = self.run_test("Get modelo tallas for comparison", "GET", f"modelos/{modelo_id}/tallas?activo=all", 200)
        
        if success and success2:
            modelo_talla_ids = [mt['talla_id'] for mt in modelo_tallas] if modelo_tallas else []
            invalid_talla_id = None
            
            for talla in all_tallas:
                if talla['id'] not in modelo_talla_ids:
                    invalid_talla_id = talla['id']
                    break
            
            if invalid_talla_id:
                bom_invalid_talla_data = {
                    "inventario_id": inventario_id,
                    "talla_id": invalid_talla_id,
                    "cantidad_base": 1.0,
                    "merma_pct": 0,
                    "orden": 3,
                    "activo": True
                }
                success, _ = self.run_test(
                    "POST BOM with invalid talla_id (should fail 400)", 
                    "POST", 
                    f"modelos/{modelo_id}/bom", 
                    400, 
                    bom_invalid_talla_data
                )
                if not success:
                    print("❌ Invalid talla validation failed")
                    return False
            else:
                print("⚠️  All tallas are associated with modelo, skipping invalid talla test")
        
        print("✅ BOM creation tests completed successfully")
        return True

    def test_bom_validations(self):
        """Test BOM validation rules"""
        print("\n🔍 Testing BOM validations...")
        
        modelo_id = self.test_data['modelo_id']
        inventario_id = self.test_data['inventario_id']
        
        # Test 14: cantidad_base <= 0 should fail
        invalid_cantidad_data = {
            "inventario_id": inventario_id,
            "talla_id": None,
            "cantidad_base": 0,
            "merma_pct": 5.0,
            "orden": 4,
            "activo": True
        }
        success, _ = self.run_test(
            "POST BOM with cantidad_base=0 (should fail 400)", 
            "POST", 
            f"modelos/{modelo_id}/bom", 
            400, 
            invalid_cantidad_data
        )
        if not success:
            print("❌ Invalid cantidad_base validation failed")
            return False
        
        # Test 14b: merma_pct > 100 should fail
        invalid_merma_data = {
            "inventario_id": inventario_id,
            "talla_id": None,
            "cantidad_base": 1.0,
            "merma_pct": 150.0,
            "orden": 5,
            "activo": True
        }
        success, _ = self.run_test(
            "POST BOM with merma_pct>100 (should fail 400)", 
            "POST", 
            f"modelos/{modelo_id}/bom", 
            400, 
            invalid_merma_data
        )
        if not success:
            print("❌ Invalid merma_pct validation failed")
            return False
        
        print("✅ BOM validation tests completed successfully")
        return True

    def test_bom_retrieval_and_deletion(self):
        """Test BOM retrieval and soft deletion"""
        print("\n📋 Testing BOM retrieval and deletion...")
        
        modelo_id = self.test_data['modelo_id']
        
        # Test 15: GET BOM with activo=true should return ordered results
        success, active_bom = self.run_test(
            "GET active BOM lines", 
            "GET", 
            f"modelos/{modelo_id}/bom?activo=true", 
            200
        )
        if not success:
            return False
        
        if not active_bom:
            print("❌ No active BOM lines found")
            return False
        
        # Validate structure includes inventory and talla names
        for bom_line in active_bom:
            if 'inventario_nombre' not in bom_line:
                print("❌ Missing inventario_nombre in BOM response")
                return False
            if bom_line.get('talla_id') and 'talla_nombre' not in bom_line:
                print("❌ Missing talla_nombre for talla-specific BOM line")
                return False
        
        print(f"✅ Found {len(active_bom)} active BOM lines with proper structure")
        
        # Test 16: DELETE (soft delete) BOM line
        if self.test_data['created_bom_lines']:
            bom_id_to_delete = self.test_data['created_bom_lines'][0]
            success, _ = self.run_test(
                "DELETE BOM line (soft delete)", 
                "DELETE", 
                f"modelos/{modelo_id}/bom/{bom_id_to_delete}", 
                200
            )
            if not success:
                return False
            
            # Test 17: GET with activo=true should not include deactivated line
            success, active_bom_after = self.run_test(
                "GET active BOM after delete", 
                "GET", 
                f"modelos/{modelo_id}/bom?activo=true", 
                200
            )
            if not success:
                return False
            
            if len(active_bom_after) >= len(active_bom):
                print("❌ BOM line was not properly deactivated")
                return False
            
            # Test 17b: GET with activo=all should include deactivated line
            success, all_bom = self.run_test(
                "GET all BOM lines", 
                "GET", 
                f"modelos/{modelo_id}/bom?activo=all", 
                200
            )
            if not success:
                return False
            
            deactivated_found = False
            for bom_line in all_bom:
                if bom_line.get('id') == bom_id_to_delete and not bom_line.get('activo'):
                    deactivated_found = True
                    break
            
            if not deactivated_found:
                print("❌ Deactivated BOM line not found in 'all' query")
                return False
        
        print("✅ BOM retrieval and deletion tests completed successfully")
        return True

    def cleanup_test_data(self):
        """Clean up created test data"""
        print("\n🧹 Cleaning up test data...")
        
        modelo_id = self.test_data['modelo_id']
        
        # Clean up BOM lines
        for bom_id in self.test_data['created_bom_lines']:
            self.run_test(
                f"Cleanup BOM line {bom_id}", 
                "DELETE", 
                f"modelos/{modelo_id}/bom/{bom_id}", 
                200
            )
        
        # Clean up modelo-talla relationships
        for rel_id in self.test_data['created_relations']:
            self.run_test(
                f"Cleanup relation {rel_id}", 
                "DELETE", 
                f"modelos/{modelo_id}/tallas/{rel_id}", 
                200
            )
        
        print("✅ Cleanup completed")

    def run_all_tests(self):
        """Run all BOM module tests"""
        print("🧪 Starting BOM Module Comprehensive Tests...")
        
        # Setup
        if not self.setup_authentication():
            return False
        
        if not self.setup_test_data():
            return False
        
        # Run test suites
        test_suites = [
            ("MODELO↔TALLAS Relationships", self.test_modelo_tallas_relationships),
            ("BOM Operations", self.test_bom_operations),
            ("BOM Validations", self.test_bom_validations),
            ("BOM Retrieval and Deletion", self.test_bom_retrieval_and_deletion)
        ]
        
        failed_suites = []
        for suite_name, test_method in test_suites:
            print(f"\n{'='*60}")
            print(f"🎯 Running {suite_name} Tests")
            print(f"{'='*60}")
            
            if not test_method():
                failed_suites.append(suite_name)
                print(f"❌ {suite_name} tests FAILED")
            else:
                print(f"✅ {suite_name} tests PASSED")
        
        # Cleanup
        self.cleanup_test_data()
        
        # Final results
        print(f"\n{'='*60}")
        print(f"📊 FINAL RESULTS")
        print(f"{'='*60}")
        print(f"Total Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if failed_suites:
            print(f"\n❌ Failed Test Suites: {', '.join(failed_suites)}")
            return False
        else:
            print(f"\n✅ All BOM Module tests PASSED!")
            return True

def main():
    tester = BOMModuleTester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())