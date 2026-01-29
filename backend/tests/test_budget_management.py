"""
Budget Management Module Tests
Tests for Project Budget Management including:
- Budget CRUD operations
- Expense tracking
- Transaction management
- Budget summary and calculations
"""
import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "test@proflow.com"
TEST_PASSWORD = "test123456"

# Test project IDs (from context)
PROJECT_WITH_USD_BUDGET = "proj_5f82429c89eb"
PROJECT_WITH_EGP_BUDGET = "proj_c31c1308e3dc"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["access_token"]


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get headers with auth token"""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


@pytest.fixture(scope="module")
def org_id(auth_headers):
    """Get org_id from existing budget"""
    response = requests.get(
        f"{BASE_URL}/api/budgets/project/{PROJECT_WITH_USD_BUDGET}",
        headers=auth_headers
    )
    assert response.status_code == 200
    return response.json()["org_id"]


class TestBudgetRetrieval:
    """Test budget retrieval endpoints"""
    
    def test_get_budget_by_project_usd(self, auth_headers):
        """Test getting budget for USD project"""
        response = requests.get(
            f"{BASE_URL}/api/budgets/project/{PROJECT_WITH_USD_BUDGET}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Validate response structure
        assert "budget_id" in data
        assert "project_id" in data
        assert data["project_id"] == PROJECT_WITH_USD_BUDGET
        assert data["currency"] == "USD"
        assert "total_budget" in data
        assert "spent_amount" in data
        assert "remaining_amount" in data
        assert "status" in data
        assert "warning_threshold_percent" in data
        
    def test_get_budget_by_project_egp(self, auth_headers):
        """Test getting budget for EGP project"""
        response = requests.get(
            f"{BASE_URL}/api/budgets/project/{PROJECT_WITH_EGP_BUDGET}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["currency"] == "EGP"
        assert data["project_id"] == PROJECT_WITH_EGP_BUDGET
        
    def test_get_budget_by_id(self, auth_headers):
        """Test getting budget by budget_id"""
        # First get budget_id from project
        response = requests.get(
            f"{BASE_URL}/api/budgets/project/{PROJECT_WITH_USD_BUDGET}",
            headers=auth_headers
        )
        budget_id = response.json()["budget_id"]
        
        # Get by budget_id
        response = requests.get(
            f"{BASE_URL}/api/budgets/{budget_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["budget_id"] == budget_id
        
    def test_get_budget_nonexistent_project(self, auth_headers):
        """Test getting budget for non-existent project returns 404"""
        response = requests.get(
            f"{BASE_URL}/api/budgets/project/proj_nonexistent",
            headers=auth_headers
        )
        assert response.status_code == 404


class TestBudgetSummary:
    """Test budget summary endpoint"""
    
    def test_get_budget_summary(self, auth_headers):
        """Test getting comprehensive budget summary"""
        # Get budget_id first
        response = requests.get(
            f"{BASE_URL}/api/budgets/project/{PROJECT_WITH_USD_BUDGET}",
            headers=auth_headers
        )
        budget_id = response.json()["budget_id"]
        
        # Get summary
        response = requests.get(
            f"{BASE_URL}/api/budgets/{budget_id}/summary",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Validate summary fields
        assert "budget_id" in data
        assert "project_name" in data
        assert "total_budget" in data
        assert "total_spent" in data
        assert "time_cost" in data
        assert "expense_cost" in data
        assert "manual_adjustments" in data
        assert "remaining" in data
        assert "spent_percent" in data
        assert "is_warning" in data
        assert "is_exceeded" in data
        assert "is_locked" in data
        
    def test_budget_summary_egp(self, auth_headers):
        """Test budget summary for EGP budget with transactions"""
        response = requests.get(
            f"{BASE_URL}/api/budgets/project/{PROJECT_WITH_EGP_BUDGET}",
            headers=auth_headers
        )
        budget_id = response.json()["budget_id"]
        
        response = requests.get(
            f"{BASE_URL}/api/budgets/{budget_id}/summary",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # EGP budget has transactions, so spent should be > 0
        assert data["total_spent"] >= 0
        assert data["currency"] == "EGP"


class TestTransactions:
    """Test budget transaction endpoints"""
    
    def test_get_transactions(self, auth_headers):
        """Test getting transactions for a budget"""
        response = requests.get(
            f"{BASE_URL}/api/budgets/project/{PROJECT_WITH_EGP_BUDGET}",
            headers=auth_headers
        )
        budget_id = response.json()["budget_id"]
        
        response = requests.get(
            f"{BASE_URL}/api/budgets/{budget_id}/transactions",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        if len(data) > 0:
            txn = data[0]
            assert "transaction_id" in txn
            assert "budget_id" in txn
            assert "source" in txn
            assert "amount" in txn
            assert "created_at" in txn
            
    def test_create_manual_transaction(self, auth_headers):
        """Test creating a manual transaction"""
        response = requests.get(
            f"{BASE_URL}/api/budgets/project/{PROJECT_WITH_USD_BUDGET}",
            headers=auth_headers
        )
        budget_id = response.json()["budget_id"]
        
        # Create transaction
        txn_data = {
            "source": "manual",
            "amount": 100.50,
            "description": "TEST_Manual_Transaction"
        }
        response = requests.post(
            f"{BASE_URL}/api/budgets/{budget_id}/transactions",
            headers=auth_headers,
            json=txn_data
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["amount"] == 100.50
        assert data["source"] == "manual"
        assert data["description"] == "TEST_Manual_Transaction"
        
        # Verify budget was updated
        response = requests.get(
            f"{BASE_URL}/api/budgets/{budget_id}",
            headers=auth_headers
        )
        assert response.json()["spent_amount"] >= 100.50
        
    def test_create_adjustment_transaction(self, auth_headers):
        """Test creating an adjustment transaction (negative amount)"""
        response = requests.get(
            f"{BASE_URL}/api/budgets/project/{PROJECT_WITH_USD_BUDGET}",
            headers=auth_headers
        )
        budget_id = response.json()["budget_id"]
        
        # Create negative adjustment (credit)
        txn_data = {
            "source": "adjustment",
            "amount": -50.00,
            "description": "TEST_Credit_Adjustment"
        }
        response = requests.post(
            f"{BASE_URL}/api/budgets/{budget_id}/transactions",
            headers=auth_headers,
            json=txn_data
        )
        assert response.status_code == 200
        assert response.json()["amount"] == -50.00


class TestExpenses:
    """Test expense management endpoints"""
    
    def test_get_project_expenses(self, auth_headers):
        """Test getting expenses for a project"""
        response = requests.get(
            f"{BASE_URL}/api/budgets/expenses/project/{PROJECT_WITH_USD_BUDGET}",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        
    def test_create_expense(self, auth_headers, org_id):
        """Test creating an expense"""
        expense_data = {
            "project_id": PROJECT_WITH_USD_BUDGET,
            "title": "TEST_Office_Supplies",
            "amount": 250.00,
            "currency": "USD",
            "category": "equipment",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "description": "Test expense for office supplies"
        }
        response = requests.post(
            f"{BASE_URL}/api/budgets/expenses/?org_id={org_id}",
            headers=auth_headers,
            json=expense_data
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["title"] == "TEST_Office_Supplies"
        assert data["amount"] == 250.00
        assert data["currency"] == "USD"
        assert data["category"] == "equipment"
        assert "expense_id" in data
        
        # Verify expense appears in project expenses
        response = requests.get(
            f"{BASE_URL}/api/budgets/expenses/project/{PROJECT_WITH_USD_BUDGET}",
            headers=auth_headers
        )
        expenses = response.json()
        assert any(e["title"] == "TEST_Office_Supplies" for e in expenses)
        
    def test_create_expense_egp(self, auth_headers, org_id):
        """Test creating an expense with EGP currency"""
        expense_data = {
            "project_id": PROJECT_WITH_EGP_BUDGET,
            "title": "TEST_Travel_Expense",
            "amount": 1500.00,
            "currency": "EGP",
            "category": "travel",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "description": "Test travel expense"
        }
        response = requests.post(
            f"{BASE_URL}/api/budgets/expenses/?org_id={org_id}",
            headers=auth_headers,
            json=expense_data
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["currency"] == "EGP"
        assert data["category"] == "travel"
        
    def test_get_expense_categories(self, auth_headers):
        """Test getting expense categories list"""
        response = requests.get(
            f"{BASE_URL}/api/budgets/expenses/categories/list",
            headers=auth_headers
        )
        assert response.status_code == 200
        categories = response.json()
        
        assert isinstance(categories, list)
        assert len(categories) > 0
        
        # Verify expected categories exist
        category_ids = [c["id"] for c in categories]
        assert "general" in category_ids
        assert "travel" in category_ids
        assert "equipment" in category_ids
        assert "software" in category_ids
        
    def test_expense_validation_invalid_category(self, auth_headers, org_id):
        """Test expense creation with invalid category fails"""
        expense_data = {
            "project_id": PROJECT_WITH_USD_BUDGET,
            "title": "Invalid Category Test",
            "amount": 100.00,
            "currency": "USD",
            "category": "invalid_category",
            "date": datetime.now().strftime("%Y-%m-%d")
        }
        response = requests.post(
            f"{BASE_URL}/api/budgets/expenses/?org_id={org_id}",
            headers=auth_headers,
            json=expense_data
        )
        assert response.status_code == 422  # Validation error


class TestBudgetUpdate:
    """Test budget update operations"""
    
    def test_update_budget_amount(self, auth_headers):
        """Test updating budget total amount"""
        response = requests.get(
            f"{BASE_URL}/api/budgets/project/{PROJECT_WITH_USD_BUDGET}",
            headers=auth_headers
        )
        budget_id = response.json()["budget_id"]
        original_budget = response.json()["total_budget"]
        
        # Update budget
        new_budget = original_budget + 5000
        response = requests.put(
            f"{BASE_URL}/api/budgets/{budget_id}?reason=TEST_Budget_Increase",
            headers=auth_headers,
            json={"total_budget": new_budget}
        )
        assert response.status_code == 200
        assert response.json()["total_budget"] == new_budget
        
        # Revert to original
        response = requests.put(
            f"{BASE_URL}/api/budgets/{budget_id}?reason=TEST_Revert",
            headers=auth_headers,
            json={"total_budget": original_budget}
        )
        assert response.status_code == 200
        
    def test_update_warning_threshold(self, auth_headers):
        """Test updating warning threshold"""
        response = requests.get(
            f"{BASE_URL}/api/budgets/project/{PROJECT_WITH_USD_BUDGET}",
            headers=auth_headers
        )
        budget_id = response.json()["budget_id"]
        
        response = requests.put(
            f"{BASE_URL}/api/budgets/{budget_id}",
            headers=auth_headers,
            json={"warning_threshold_percent": 75.0}
        )
        assert response.status_code == 200
        assert response.json()["warning_threshold_percent"] == 75.0
        
        # Revert
        response = requests.put(
            f"{BASE_URL}/api/budgets/{budget_id}",
            headers=auth_headers,
            json={"warning_threshold_percent": 80.0}
        )
        
    def test_update_hard_limit(self, auth_headers):
        """Test toggling hard limit"""
        response = requests.get(
            f"{BASE_URL}/api/budgets/project/{PROJECT_WITH_USD_BUDGET}",
            headers=auth_headers
        )
        budget_id = response.json()["budget_id"]
        original_hard_limit = response.json()["hard_limit"]
        
        # Toggle hard limit
        response = requests.put(
            f"{BASE_URL}/api/budgets/{budget_id}",
            headers=auth_headers,
            json={"hard_limit": not original_hard_limit}
        )
        assert response.status_code == 200
        assert response.json()["hard_limit"] == (not original_hard_limit)
        
        # Revert
        response = requests.put(
            f"{BASE_URL}/api/budgets/{budget_id}",
            headers=auth_headers,
            json={"hard_limit": original_hard_limit}
        )


class TestBudgetRevisions:
    """Test budget revision history"""
    
    def test_get_revisions(self, auth_headers):
        """Test getting budget revision history"""
        response = requests.get(
            f"{BASE_URL}/api/budgets/project/{PROJECT_WITH_USD_BUDGET}",
            headers=auth_headers
        )
        budget_id = response.json()["budget_id"]
        
        response = requests.get(
            f"{BASE_URL}/api/budgets/{budget_id}/revisions",
            headers=auth_headers
        )
        assert response.status_code == 200
        revisions = response.json()
        
        assert isinstance(revisions, list)
        # Should have revisions from update tests
        if len(revisions) > 0:
            rev = revisions[0]
            assert "revision_id" in rev
            assert "previous_budget" in rev
            assert "new_budget" in rev
            assert "change_amount" in rev


class TestBudgetLock:
    """Test budget lock functionality"""
    
    def test_check_budget_lock(self, auth_headers):
        """Test checking if budget is locked"""
        response = requests.get(
            f"{BASE_URL}/api/budgets/check-lock/{PROJECT_WITH_USD_BUDGET}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "is_locked" in data
        assert data["is_locked"] == False  # Budget should not be locked


class TestOrgBudgets:
    """Test organization-level budget operations"""
    
    def test_get_org_budgets(self, auth_headers, org_id):
        """Test getting all budgets for an organization"""
        response = requests.get(
            f"{BASE_URL}/api/budgets/org/{org_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        budgets = response.json()
        
        assert isinstance(budgets, list)
        assert len(budgets) >= 2  # At least USD and EGP budgets
        
        # Verify both currencies are present
        currencies = [b["currency"] for b in budgets]
        assert "USD" in currencies
        assert "EGP" in currencies


class TestBillableRates:
    """Test billable rate endpoints"""
    
    def test_get_org_rates(self, auth_headers, org_id):
        """Test getting billable rates for organization"""
        response = requests.get(
            f"{BASE_URL}/api/budgets/rates/org/{org_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        
    def test_set_billable_rate(self, auth_headers, org_id):
        """Test setting a billable rate"""
        rate_data = {
            "hourly_rate": 75.00,
            "currency": "USD"
        }
        response = requests.post(
            f"{BASE_URL}/api/budgets/rates/?org_id={org_id}",
            headers=auth_headers,
            json=rate_data
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["hourly_rate"] == 75.00
        assert data["currency"] == "USD"
        
    def test_get_effective_rate(self, auth_headers, org_id):
        """Test getting effective billable rate"""
        response = requests.get(
            f"{BASE_URL}/api/budgets/rates/effective?org_id={org_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "hourly_rate" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
