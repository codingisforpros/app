import requests
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

class WealthTrackerAPITester:
    def __init__(self, base_url="https://4b25a806-606b-4ec1-8bd5-f2bd0de2b48b.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.token = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_user_email = f"test_user_{datetime.now().strftime('%Y%m%d_%H%M%S')}@example.com"
        self.test_user_password = "TestPass123!"
        self.test_user_name = "Test User"
        self.created_assets = []
        self.created_milestones = []

    def log_test(self, name: str, success: bool, details: str = ""):
        """Log test results"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED {details}")
        else:
            print(f"❌ {name} - FAILED {details}")
        return success

    def make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, 
                    expected_status: int = 200, auth_required: bool = False) -> tuple[bool, Dict]:
        """Make HTTP request and validate response"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if auth_required and self.token:
            headers['Authorization'] = f'Bearer {self.token}'

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10)
            else:
                return False, {"error": f"Unsupported method: {method}"}

            success = response.status_code == expected_status
            try:
                response_data = response.json()
            except:
                response_data = {"status_code": response.status_code, "text": response.text}

            return success, response_data

        except requests.exceptions.RequestException as e:
            return False, {"error": str(e)}

    def test_user_registration(self) -> bool:
        """Test user registration"""
        data = {
            "name": self.test_user_name,
            "email": self.test_user_email,
            "password": self.test_user_password
        }
        
        success, response = self.make_request("POST", "register", data, 200)
        
        if success and "access_token" in response:
            self.token = response["access_token"]
            return self.log_test("User Registration", True, f"Token received")
        else:
            return self.log_test("User Registration", False, f"Response: {response}")

    def test_user_login(self) -> bool:
        """Test user login"""
        data = {
            "email": self.test_user_email,
            "password": self.test_user_password
        }
        
        success, response = self.make_request("POST", "login", data, 200)
        
        if success and "access_token" in response:
            self.token = response["access_token"]
            return self.log_test("User Login", True, f"Token received")
        else:
            return self.log_test("User Login", False, f"Response: {response}")

    def test_invalid_login(self) -> bool:
        """Test login with invalid credentials"""
        data = {
            "email": "invalid@example.com",
            "password": "wrongpassword"
        }
        
        success, response = self.make_request("POST", "login", data, 401)
        return self.log_test("Invalid Login", success, f"Correctly rejected invalid credentials")

    def test_get_user_profile(self) -> bool:
        """Test getting user profile"""
        success, response = self.make_request("GET", "me", auth_required=True)
        
        if success and "email" in response and response["email"] == self.test_user_email:
            self.user_id = response.get("id")
            return self.log_test("Get User Profile", True, f"User data retrieved")
        else:
            return self.log_test("Get User Profile", False, f"Response: {response}")

    def test_create_asset(self, asset_type: str = "stocks") -> Optional[str]:
        """Test creating an asset"""
        data = {
            "asset_type": asset_type,
            "name": f"Test {asset_type.title()} Asset",
            "purchase_value": 10000.0,
            "current_value": 12000.0,
            "purchase_date": (datetime.now() - timedelta(days=30)).isoformat(),
            "metadata": {"test": True}
        }
        
        success, response = self.make_request("POST", "assets", data, 200, auth_required=True)
        
        if success and "id" in response:
            asset_id = response["id"]
            self.created_assets.append(asset_id)
            self.log_test(f"Create {asset_type} Asset", True, f"Asset ID: {asset_id}")
            return asset_id
        else:
            self.log_test(f"Create {asset_type} Asset", False, f"Response: {response}")
            return None

    def test_get_assets(self) -> bool:
        """Test getting all assets"""
        success, response = self.make_request("GET", "assets", auth_required=True)
        
        if success and isinstance(response, list):
            return self.log_test("Get Assets", True, f"Retrieved {len(response)} assets")
        else:
            return self.log_test("Get Assets", False, f"Response: {response}")

    def test_get_single_asset(self, asset_id: str) -> bool:
        """Test getting a single asset"""
        success, response = self.make_request("GET", f"assets/{asset_id}", auth_required=True)
        
        if success and "id" in response and response["id"] == asset_id:
            return self.log_test("Get Single Asset", True, f"Asset retrieved: {response['name']}")
        else:
            return self.log_test("Get Single Asset", False, f"Response: {response}")

    def test_update_asset(self, asset_id: str) -> bool:
        """Test updating an asset"""
        data = {
            "name": "Updated Test Asset",
            "current_value": 15000.0
        }
        
        success, response = self.make_request("PUT", f"assets/{asset_id}", data, 200, auth_required=True)
        
        if success and "name" in response and response["name"] == "Updated Test Asset":
            return self.log_test("Update Asset", True, f"Asset updated successfully")
        else:
            return self.log_test("Update Asset", False, f"Response: {response}")

    def test_dashboard(self) -> bool:
        """Test dashboard endpoint"""
        success, response = self.make_request("GET", "dashboard", auth_required=True)
        
        expected_fields = ["total_net_worth", "total_investment", "total_gain_loss", 
                          "gain_loss_percentage", "asset_allocation", "recent_assets"]
        
        if success and all(field in response for field in expected_fields):
            return self.log_test("Dashboard", True, 
                               f"Net worth: {response['total_net_worth']}, "
                               f"Investment: {response['total_investment']}")
        else:
            return self.log_test("Dashboard", False, f"Response: {response}")

    def test_delete_asset(self, asset_id: str) -> bool:
        """Test deleting an asset"""
        success, response = self.make_request("DELETE", f"assets/{asset_id}", expected_status=200, auth_required=True)
        
        if success and "message" in response:
            return self.log_test("Delete Asset", True, f"Asset deleted successfully")
        else:
            return self.log_test("Delete Asset", False, f"Response: {response}")

    def test_unauthorized_access(self) -> bool:
        """Test accessing protected endpoints without token"""
        # Temporarily remove token
        original_token = self.token
        self.token = None
        
        success, response = self.make_request("GET", "me", expected_status=403, auth_required=True)
        
        # Restore token
        self.token = original_token
        
        return self.log_test("Unauthorized Access", success, "Correctly rejected unauthorized request")

    def test_asset_types(self) -> bool:
        """Test creating assets of different types"""
        asset_types = ["stocks", "mutual_funds", "cryptocurrency", "real_estate", 
                      "fixed_deposits", "gold", "others"]
        
        all_success = True
        for asset_type in asset_types:
            asset_id = self.test_create_asset(asset_type)
            if not asset_id:
                all_success = False
        
        return all_success

    def cleanup_test_data(self):
        """Clean up created test data"""
        print(f"\n🧹 Cleaning up test data...")
        for asset_id in self.created_assets:
            self.test_delete_asset(asset_id)

    def run_all_tests(self) -> int:
        """Run all tests"""
        print(f"🚀 Starting Wealth Tracker API Tests")
        print(f"📍 Testing against: {self.base_url}")
        print(f"👤 Test user: {self.test_user_email}")
        print("=" * 60)

        # Authentication Tests
        print(f"\n📝 Authentication Tests")
        if not self.test_user_registration():
            print("❌ Registration failed, stopping tests")
            return 1

        if not self.test_get_user_profile():
            print("❌ Profile fetch failed, stopping tests")
            return 1

        self.test_invalid_login()
        self.test_user_login()  # Test login with existing user
        self.test_unauthorized_access()

        # Asset Management Tests
        print(f"\n📊 Asset Management Tests")
        
        # Test different asset types
        self.test_asset_types()
        
        # Test CRUD operations with first created asset
        if self.created_assets:
            first_asset = self.created_assets[0]
            self.test_get_single_asset(first_asset)
            self.test_update_asset(first_asset)
        
        self.test_get_assets()

        # Dashboard Tests
        print(f"\n📈 Dashboard Tests")
        self.test_dashboard()

        # Cleanup
        self.cleanup_test_data()

        # Results
        print("\n" + "=" * 60)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return 0
        else:
            print(f"⚠️  {self.tests_run - self.tests_passed} tests failed")
            return 1

def main():
    tester = WealthTrackerAPITester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())