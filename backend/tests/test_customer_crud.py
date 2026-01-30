"""
Customer CRUD Tests
Tests for verifying the Customer module bug fixes:
1. Create Customer - MongoDB _id serialization fix
2. Edit Customer - phone/contact field mapping fix
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://costmanager-5.preview.emergentagent.com').rstrip('/')

# Test credentials
TEST_EMAIL = "test@proflow.com"
TEST_PASSWORD = "test123456"


class TestCustomerCRUD:
    """Test Customer CRUD operations - Bug fix verification"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        return response.json()["access_token"]
    
    @pytest.fixture
    def org_id(self, auth_token):
        """Get organization ID from organizations endpoint"""
        response = requests.get(f"{BASE_URL}/api/organizations/", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        assert response.status_code == 200
        orgs = response.json()
        assert len(orgs) > 0, "No organizations found for user"
        return orgs[0]["org_id"]
    
    def test_create_customer_no_mongodb_id_leak(self, auth_token, org_id):
        """
        BUG FIX TEST: Create customer should NOT return MongoDB _id
        This was the first bug - MongoDB _id was not being removed before JSON response
        """
        unique_name = f"TEST_Customer_{uuid.uuid4().hex[:8]}"
        
        response = requests.post(
            f"{BASE_URL}/api/customers/?org_id={org_id}",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "name": unique_name,
                "email": f"test_{uuid.uuid4().hex[:6]}@example.com",
                "phone": "+1-555-123-4567",
                "company": "Test Company",
                "address": "123 Test St",
                "notes": "Test customer for bug fix verification"
            }
        )
        
        assert response.status_code == 200, f"Create customer failed: {response.text}"
        data = response.json()
        
        # BUG FIX VERIFICATION: No MongoDB _id in response
        assert "_id" not in data, "BUG: MongoDB _id should NOT be in response"
        
        # Verify customer_id is present
        assert "customer_id" in data, "customer_id should be in response"
        assert data["customer_id"].startswith("cust_"), "customer_id should start with 'cust_'"
        
        # Verify all fields are returned correctly
        assert data["name"] == unique_name
        assert data["phone"] == "+1-555-123-4567"
        
        print(f"✓ Create customer working - no _id leak, customer_id: {data['customer_id']}")
        
        # Cleanup - delete the test customer
        delete_response = requests.delete(
            f"{BASE_URL}/api/customers/{data['customer_id']}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert delete_response.status_code == 200, f"Cleanup failed: {delete_response.text}"
        
        return data["customer_id"]
    
    def test_create_customer_with_phone_field(self, auth_token, org_id):
        """
        BUG FIX TEST: Create customer with phone field should work
        Backend expects 'phone' field, frontend sends 'contact' (mapped in API layer)
        """
        unique_name = f"TEST_PhoneCustomer_{uuid.uuid4().hex[:8]}"
        test_phone = "+1-555-987-6543"
        
        response = requests.post(
            f"{BASE_URL}/api/customers/?org_id={org_id}",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "name": unique_name,
                "email": f"phone_test_{uuid.uuid4().hex[:6]}@example.com",
                "phone": test_phone,  # Backend expects 'phone'
                "company": "Phone Test Company"
            }
        )
        
        assert response.status_code == 200, f"Create customer failed: {response.text}"
        data = response.json()
        
        # Verify phone field is saved and returned correctly
        assert data["phone"] == test_phone, f"Phone field mismatch: expected {test_phone}, got {data.get('phone')}"
        
        print(f"✓ Create customer with phone field working - phone: {data['phone']}")
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/customers/{data['customer_id']}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        return data
    
    def test_update_customer_phone_field(self, auth_token, org_id):
        """
        BUG FIX TEST: Update customer phone/contact field should persist
        This was the second bug - frontend used 'contact' but backend used 'phone'
        """
        # First create a customer
        unique_name = f"TEST_UpdateCustomer_{uuid.uuid4().hex[:8]}"
        
        create_response = requests.post(
            f"{BASE_URL}/api/customers/?org_id={org_id}",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "name": unique_name,
                "email": f"update_test_{uuid.uuid4().hex[:6]}@example.com",
                "phone": "+1-555-111-1111",
                "company": "Update Test Company"
            }
        )
        
        assert create_response.status_code == 200, f"Create failed: {create_response.text}"
        customer = create_response.json()
        customer_id = customer["customer_id"]
        
        # Now update the phone number
        new_phone = "+1-555-999-8888"
        update_response = requests.put(
            f"{BASE_URL}/api/customers/{customer_id}",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "name": unique_name,
                "email": customer["email"],
                "phone": new_phone,  # Backend expects 'phone'
                "company": "Updated Company Name"
            }
        )
        
        assert update_response.status_code == 200, f"Update failed: {update_response.text}"
        updated_customer = update_response.json()
        
        # BUG FIX VERIFICATION: Phone field should be updated
        assert updated_customer["phone"] == new_phone, f"Phone update failed: expected {new_phone}, got {updated_customer.get('phone')}"
        
        # Verify via GET to ensure persistence
        get_response = requests.get(
            f"{BASE_URL}/api/customers/{customer_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert get_response.status_code == 200
        fetched_customer = get_response.json()
        assert fetched_customer["phone"] == new_phone, f"Phone not persisted: expected {new_phone}, got {fetched_customer.get('phone')}"
        
        print(f"✓ Update customer phone field working - phone updated to: {new_phone}")
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/customers/{customer_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
    
    def test_get_customers_list_with_phone(self, auth_token, org_id):
        """Test that customer list returns phone field correctly"""
        response = requests.get(
            f"{BASE_URL}/api/customers/?org_id={org_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200, f"Get customers failed: {response.text}"
        customers = response.json()
        
        assert isinstance(customers, list), "Response should be a list"
        
        # Verify no _id leak in any customer
        for customer in customers:
            assert "_id" not in customer, f"MongoDB _id found in customer: {customer.get('customer_id')}"
            assert "customer_id" in customer, "customer_id should be present"
        
        print(f"✓ Get customers list working - found {len(customers)} customers, no _id leak")
    
    def test_get_single_customer_with_phone(self, auth_token, org_id):
        """Test that single customer GET returns phone field correctly"""
        # First create a customer with phone
        unique_name = f"TEST_GetCustomer_{uuid.uuid4().hex[:8]}"
        test_phone = "+1-555-GET-TEST"
        
        create_response = requests.post(
            f"{BASE_URL}/api/customers/?org_id={org_id}",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "name": unique_name,
                "phone": test_phone
            }
        )
        
        assert create_response.status_code == 200
        customer_id = create_response.json()["customer_id"]
        
        # Get the customer
        get_response = requests.get(
            f"{BASE_URL}/api/customers/{customer_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert get_response.status_code == 200, f"Get customer failed: {get_response.text}"
        customer = get_response.json()
        
        # Verify phone field
        assert customer["phone"] == test_phone, f"Phone mismatch: expected {test_phone}, got {customer.get('phone')}"
        assert "_id" not in customer, "MongoDB _id should not be in response"
        
        print(f"✓ Get single customer working - phone: {customer['phone']}")
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/customers/{customer_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
    
    def test_delete_customer(self, auth_token, org_id):
        """Test customer deletion works correctly"""
        # Create a customer to delete
        unique_name = f"TEST_DeleteCustomer_{uuid.uuid4().hex[:8]}"
        
        create_response = requests.post(
            f"{BASE_URL}/api/customers/?org_id={org_id}",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "name": unique_name,
                "phone": "+1-555-DELETE"
            }
        )
        
        assert create_response.status_code == 200
        customer_id = create_response.json()["customer_id"]
        
        # Delete the customer
        delete_response = requests.delete(
            f"{BASE_URL}/api/customers/{customer_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert delete_response.status_code == 200, f"Delete failed: {delete_response.text}"
        
        # Verify customer is deleted
        get_response = requests.get(
            f"{BASE_URL}/api/customers/{customer_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert get_response.status_code == 404, "Deleted customer should return 404"
        
        print(f"✓ Delete customer working - customer {customer_id} deleted successfully")
    
    def test_full_crud_cycle_with_phone(self, auth_token, org_id):
        """
        Full CRUD cycle test - Create, Read, Update, Delete with phone field
        This is the comprehensive test for the bug fixes
        """
        # CREATE
        unique_name = f"TEST_FullCRUD_{uuid.uuid4().hex[:8]}"
        original_phone = "+1-555-ORIGINAL"
        
        create_response = requests.post(
            f"{BASE_URL}/api/customers/?org_id={org_id}",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "name": unique_name,
                "email": f"crud_test_{uuid.uuid4().hex[:6]}@example.com",
                "phone": original_phone,
                "company": "CRUD Test Company",
                "address": "456 CRUD St",
                "notes": "Full CRUD cycle test"
            }
        )
        
        assert create_response.status_code == 200, f"CREATE failed: {create_response.text}"
        created = create_response.json()
        assert "_id" not in created, "CREATE: MongoDB _id leak"
        assert created["phone"] == original_phone, "CREATE: Phone not saved"
        customer_id = created["customer_id"]
        print(f"  CREATE: ✓ customer_id={customer_id}, phone={created['phone']}")
        
        # READ
        read_response = requests.get(
            f"{BASE_URL}/api/customers/{customer_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert read_response.status_code == 200, f"READ failed: {read_response.text}"
        read_data = read_response.json()
        assert read_data["phone"] == original_phone, "READ: Phone mismatch"
        assert "_id" not in read_data, "READ: MongoDB _id leak"
        print(f"  READ: ✓ phone={read_data['phone']}")
        
        # UPDATE
        updated_phone = "+1-555-UPDATED"
        update_response = requests.put(
            f"{BASE_URL}/api/customers/{customer_id}",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "name": unique_name + "_Updated",
                "email": created["email"],
                "phone": updated_phone,
                "company": "Updated CRUD Company",
                "address": created["address"],
                "notes": "Updated notes"
            }
        )
        
        assert update_response.status_code == 200, f"UPDATE failed: {update_response.text}"
        updated = update_response.json()
        assert updated["phone"] == updated_phone, f"UPDATE: Phone not updated, got {updated.get('phone')}"
        assert "_id" not in updated, "UPDATE: MongoDB _id leak"
        print(f"  UPDATE: ✓ phone updated to {updated['phone']}")
        
        # VERIFY UPDATE PERSISTED
        verify_response = requests.get(
            f"{BASE_URL}/api/customers/{customer_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert verify_response.status_code == 200
        verified = verify_response.json()
        assert verified["phone"] == updated_phone, "UPDATE: Phone not persisted"
        print(f"  VERIFY: ✓ phone persisted as {verified['phone']}")
        
        # DELETE
        delete_response = requests.delete(
            f"{BASE_URL}/api/customers/{customer_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert delete_response.status_code == 200, f"DELETE failed: {delete_response.text}"
        
        # VERIFY DELETE
        verify_delete = requests.get(
            f"{BASE_URL}/api/customers/{customer_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert verify_delete.status_code == 404, "DELETE: Customer still exists"
        print(f"  DELETE: ✓ customer deleted")
        
        print(f"✓ Full CRUD cycle completed successfully")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
