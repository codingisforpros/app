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

    def test_gold_prices_api(self) -> bool:
        """Test gold prices API endpoint"""
        success, response = self.make_request("GET", "gold-prices", expected_status=200)
        
        if success and all(field in response for field in ["gold_22k", "gold_24k", "timestamp", "unit"]):
            return self.log_test("Gold Prices API", True, 
                               f"22K: ₹{response['gold_22k']}, 24K: ₹{response['gold_24k']}")
        else:
            return self.log_test("Gold Prices API", False, f"Response: {response}")

    def test_gold_value_calculation(self) -> bool:
        """Test gold value calculation endpoint"""
        success, response = self.make_request("POST", "gold/calculate-value?weight_grams=50&purity=24k", 
                                            expected_status=200)
        
        if success and all(field in response for field in ["weight_grams", "purity", "rate_per_gram", "current_value"]):
            return self.log_test("Gold Value Calculation", True, 
                               f"50g 24K = ₹{response['current_value']}")
        else:
            return self.log_test("Gold Value Calculation", False, f"Response: {response}")

    def test_create_gold_asset(self) -> Optional[str]:
        """Test creating a gold asset with auto-calculation"""
        data = {
            "asset_type": "gold",
            "name": "Test Gold Jewelry",
            "purchase_value": 250000.0,
            "current_value": 0.0,  # Should be auto-calculated
            "purchase_date": (datetime.now() - timedelta(days=30)).isoformat(),
            "metadata": {
                "weight_grams": 50.0,
                "purity": "22k"
            }
        }
        
        success, response = self.make_request("POST", "assets", data, 200, auth_required=True)
        
        if success and "id" in response:
            asset_id = response["id"]
            self.created_assets.append(asset_id)
            auto_calculated = response.get("metadata", {}).get("auto_calculated", False)
            current_value = response.get("current_value", 0)
            
            if auto_calculated and current_value > 0:
                self.log_test("Create Gold Asset", True, 
                             f"Auto-calculated value: ₹{current_value}")
                return asset_id
            else:
                self.log_test("Create Gold Asset", False, 
                             f"Auto-calculation failed. Value: {current_value}, Auto: {auto_calculated}")
                return asset_id
        else:
            self.log_test("Create Gold Asset", False, f"Response: {response}")
            return None

    def test_create_milestone(self) -> Optional[str]:
        """Test creating a financial milestone"""
        data = {
            "name": "₹1 Crore Net Worth Goal",
            "target_amount": 10000000.0,
            "target_date": (datetime.now() + timedelta(days=365*5)).isoformat()
        }
        
        success, response = self.make_request("POST", "milestones", data, 200, auth_required=True)
        
        if success and "id" in response:
            milestone_id = response["id"]
            self.created_milestones.append(milestone_id)
            return self.log_test("Create Milestone", True, 
                               f"Target: ₹{response['target_amount']}")
        else:
            return self.log_test("Create Milestone", False, f"Response: {response}")

    def test_get_milestones(self) -> bool:
        """Test getting all milestones"""
        success, response = self.make_request("GET", "milestones", auth_required=True)
        
        if success and isinstance(response, list):
            return self.log_test("Get Milestones", True, f"Retrieved {len(response)} milestones")
        else:
            return self.log_test("Get Milestones", False, f"Response: {response}")

    def test_projections_calculation(self) -> bool:
        """Test net worth projections calculation"""
        projection_data = [
            {
                "asset_class": "stocks",
                "current_value": 100000.0,
                "annual_growth_rate": 12.0,
                "annual_investment": 50000.0,
                "years": 10
            },
            {
                "asset_class": "gold",
                "current_value": 250000.0,
                "annual_growth_rate": 8.0,
                "annual_investment": 25000.0,
                "years": 10
            }
        ]
        
        success, response = self.make_request("POST", "projections/calculate", projection_data, 
                                            200, auth_required=True)
        
        if success and isinstance(response, list) and len(response) >= 10:
            year_10 = response[9]
            return self.log_test("Projections Calculation", True, 
                               f"Year 10 projection: ₹{year_10['total_value']:.0f}")
        else:
            return self.log_test("Projections Calculation", False, f"Response: {response}")

    def test_create_sip_asset(self) -> Optional[str]:
        """Test creating an asset with SIP enabled"""
        data = {
            "asset_type": "mutual_funds",
            "name": "Test SIP Mutual Fund",
            "purchase_value": 5000.0,
            "current_value": 5500.0,
            "purchase_date": (datetime.now() - timedelta(days=30)).isoformat(),
            "metadata": {"fund_type": "equity"},
            # SIP fields
            "monthly_sip_amount": 5000.0,
            "sip_start_date": datetime.now().isoformat(),
            "step_up_percentage": 10.0,
            "is_sip_active": True
        }
        
        success, response = self.make_request("POST", "assets", data, 200, auth_required=True)
        
        if success and "id" in response:
            asset_id = response["id"]
            self.created_assets.append(asset_id)
            
            # Verify SIP fields are saved correctly
            sip_amount = response.get("monthly_sip_amount", 0)
            step_up = response.get("step_up_percentage", 0)
            is_active = response.get("is_sip_active", False)
            
            if sip_amount == 5000.0 and step_up == 10.0 and is_active:
                self.log_test("Create SIP Asset", True, 
                             f"SIP: ₹{sip_amount}/month, Step-up: {step_up}%")
                return asset_id
            else:
                self.log_test("Create SIP Asset", False, 
                             f"SIP fields incorrect: Amount={sip_amount}, Step-up={step_up}, Active={is_active}")
                return asset_id
        else:
            self.log_test("Create SIP Asset", False, f"Response: {response}")
            return None

    def test_update_sip_asset(self, asset_id: str) -> bool:
        """Test updating SIP configuration of an asset"""
        data = {
            "name": "Updated SIP Mutual Fund",
            "current_value": 6000.0,
            "monthly_sip_amount": 7000.0,
            "step_up_percentage": 15.0,
            "is_sip_active": True
        }
        
        success, response = self.make_request("PUT", f"assets/{asset_id}", data, 200, auth_required=True)
        
        if success and "monthly_sip_amount" in response:
            sip_amount = response.get("monthly_sip_amount", 0)
            step_up = response.get("step_up_percentage", 0)
            
            if sip_amount == 7000.0 and step_up == 15.0:
                return self.log_test("Update SIP Asset", True, 
                                   f"Updated SIP: ₹{sip_amount}/month, Step-up: {step_up}%")
            else:
                return self.log_test("Update SIP Asset", False, 
                                   f"SIP update failed: Amount={sip_amount}, Step-up={step_up}")
        else:
            return self.log_test("Update SIP Asset", False, f"Response: {response}")

    def test_sip_projections_calculation(self) -> bool:
        """Test net worth projections with SIP calculations"""
        projection_data = [
            {
                "asset_class": "mutual_funds",
                "current_value": 50000.0,
                "annual_growth_rate": 12.0,
                "annual_investment": 10000.0,
                "years": 10,
                # SIP fields
                "monthly_sip_amount": 5000.0,
                "step_up_percentage": 10.0
            },
            {
                "asset_class": "stocks",
                "current_value": 100000.0,
                "annual_growth_rate": 15.0,
                "annual_investment": 20000.0,
                "years": 10,
                # SIP fields
                "monthly_sip_amount": 3000.0,
                "step_up_percentage": 5.0
            }
        ]
        
        success, response = self.make_request("POST", "projections/calculate", projection_data, 
                                            200, auth_required=True)
        
        if success and isinstance(response, list) and len(response) >= 10:
            year_1 = response[0]
            year_10 = response[9]
            
            # Check if SIP contributions are tracked separately
            has_sip_tracking = ("sip_contribution" in year_1 and 
                              "lumpsum_contribution" in year_1)
            
            if has_sip_tracking:
                total_sip_year_10 = year_10.get("sip_contribution", 0)
                total_lumpsum_year_10 = year_10.get("lumpsum_contribution", 0)
                
                return self.log_test("SIP Projections Calculation", True, 
                                   f"Year 10: Total=₹{year_10['total_value']:.0f}, "
                                   f"SIP=₹{total_sip_year_10:.0f}, "
                                   f"Lumpsum=₹{total_lumpsum_year_10:.0f}")
            else:
                return self.log_test("SIP Projections Calculation", False, 
                                   "SIP tracking fields missing in response")
        else:
            return self.log_test("SIP Projections Calculation", False, f"Response: {response}")

    def test_advanced_analytics_monte_carlo(self) -> bool:
        """Test Monte Carlo simulation endpoint"""
        params = {
            "initial_value": 500000,
            "annual_return": 12,
            "volatility": 15,
            "annual_investment": 100000,
            "years": 20
        }
        
        success, response = self.make_request("GET", "analytics/monte-carlo", params, 200, auth_required=True)
        
        if success and "percentile_10" in response:
            monte_carlo = response
            required_fields = ["percentile_10", "percentile_25", "percentile_50", "percentile_75", "percentile_90", "years", "final_values"]
            all_present = all(field in monte_carlo for field in required_fields)
            
            if all_present:
                final_values = monte_carlo["final_values"]
                return self.log_test("Monte Carlo Simulation", True, 
                                   f"Range: ₹{final_values['worst_case']:,.0f} - ₹{final_values['best_case']:,.0f}")
            else:
                return self.log_test("Monte Carlo Simulation", False, "Missing required fields")
        else:
            return self.log_test("Monte Carlo Simulation", False, f"Response: {response}")

    def test_advanced_analytics_health_score(self) -> bool:
        """Test financial health score calculation"""
        success, response = self.make_request("GET", "analytics/financial-health-score", auth_required=True)
        
        if success and "overall_score" in response:
            health_score = response
            required_fields = ["overall_score", "category_scores", "recommendations", "strengths"]
            all_present = all(field in health_score for field in required_fields)
            score_valid = 0 <= health_score["overall_score"] <= 1000
            
            if all_present and score_valid:
                return self.log_test("Financial Health Score", True, 
                                   f"Score: {health_score['overall_score']}/1000")
            else:
                return self.log_test("Financial Health Score", False, 
                                   f"Invalid structure or score: {health_score['overall_score']}")
        else:
            return self.log_test("Financial Health Score", False, f"Response: {response}")

    def test_advanced_analytics_performance(self) -> bool:
        """Test performance attribution analysis"""
        success, response = self.make_request("GET", "analytics/performance-attribution", auth_required=True)
        
        if success and "asset_contributions" in response:
            performance = response
            required_fields = ["asset_contributions", "sector_analysis", "best_performers", "worst_performers"]
            all_present = all(field in performance for field in required_fields)
            
            if all_present:
                best_count = len(performance.get("best_performers", []))
                sector_count = len(performance.get("sector_analysis", {}))
                return self.log_test("Performance Attribution", True, 
                                   f"Best performers: {best_count}, Sectors: {sector_count}")
            else:
                return self.log_test("Performance Attribution", False, "Missing required fields")
        else:
            return self.log_test("Performance Attribution", False, f"Response: {response}")

    def test_advanced_analytics_tax_optimization(self) -> bool:
        """Test tax optimization analysis"""
        success, response = self.make_request("GET", "analytics/tax-optimization", auth_required=True)
        
        if success and "total_tax_liability" in response:
            tax_data = response
            required_fields = ["ltcg_liability", "stcg_liability", "tax_saving_opportunities", "total_tax_liability"]
            all_present = all(field in tax_data for field in required_fields)
            
            if all_present:
                return self.log_test("Tax Optimization", True, 
                                   f"Tax Liability: ₹{tax_data['total_tax_liability']:,.0f}, "
                                   f"Rate: {tax_data['effective_tax_rate']:.2f}%")
            else:
                return self.log_test("Tax Optimization", False, "Missing required fields")
        else:
            return self.log_test("Tax Optimization", False, f"Response: {response}")

    def test_advanced_analytics_comprehensive_report(self) -> bool:
        """Test comprehensive analytics report"""
        success, response = self.make_request("GET", "analytics/comprehensive-report", auth_required=True)
        
        if success and "monte_carlo" in response:
            report = response
            required_sections = ["monte_carlo", "financial_health_score", "performance_attribution", "tax_optimization"]
            all_present = all(section in report for section in required_sections)
            
            if all_present:
                return self.log_test("Comprehensive Analytics Report", True, 
                                   f"Sections: {list(report.keys())}")
            else:
                return self.log_test("Comprehensive Analytics Report", False, "Missing required sections")
        else:
            return self.log_test("Comprehensive Analytics Report", False, f"Response: {response}")

    def test_step_up_sip_calculation(self) -> bool:
        """Test step-up SIP calculation logic"""
        projection_data = [
            {
                "asset_class": "mutual_funds",
                "current_value": 0.0,  # Start with zero to see pure SIP effect
                "annual_growth_rate": 12.0,
                "annual_investment": 0.0,  # No lumpsum
                "years": 3,
                "monthly_sip_amount": 1000.0,  # ₹1000/month
                "step_up_percentage": 20.0  # 20% annual increase
            }
        ]
        
        success, response = self.make_request("POST", "projections/calculate", projection_data, 
                                            200, auth_required=True)
        
        if success and isinstance(response, list) and len(response) >= 3:
            year_1_sip = response[0].get("sip_contribution", 0)
            year_2_sip = response[1].get("sip_contribution", 0)
            year_3_sip = response[2].get("sip_contribution", 0)
            
            # Year 1: 12 * 1000 = 12,000
            # Year 2: 12 * 1200 = 14,400 (20% step-up)
            # Year 3: 12 * 1440 = 17,280 (another 20% step-up)
            
            expected_year_1 = 12000
            expected_year_2 = 14400
            expected_year_3 = 17280
            
            tolerance = 100  # Allow small rounding differences
            
            year_1_ok = abs(year_1_sip - expected_year_1) <= tolerance
            year_2_ok = abs(year_2_sip - expected_year_2) <= tolerance
            year_3_ok = abs(year_3_sip - expected_year_3) <= tolerance
            
            if year_1_ok and year_2_ok and year_3_ok:
                return self.log_test("Step-up SIP Calculation", True, 
                                   f"Y1: ₹{year_1_sip:.0f}, Y2: ₹{year_2_sip:.0f}, Y3: ₹{year_3_sip:.0f}")
            else:
                return self.log_test("Step-up SIP Calculation", False, 
                                   f"Expected Y1: ₹{expected_year_1}, Y2: ₹{expected_year_2}, Y3: ₹{expected_year_3} "
                                   f"Got Y1: ₹{year_1_sip:.0f}, Y2: ₹{year_2_sip:.0f}, Y3: ₹{year_3_sip:.0f}")
        else:
            return self.log_test("Step-up SIP Calculation", False, f"Response: {response}")

    def test_dashboard_with_gold_updates(self) -> bool:
        """Test dashboard with gold price auto-updates"""
        success, response = self.make_request("GET", "dashboard", auth_required=True)
        
        expected_fields = ["total_net_worth", "total_investment", "total_gain_loss", 
                          "gain_loss_percentage", "asset_allocation", "recent_assets"]
        
        if success and all(field in response for field in expected_fields):
            # Check if any gold assets have auto-updated values
            gold_auto_updated = False
            for asset in response.get("recent_assets", []):
                if (asset.get("asset_type") == "gold" and 
                    asset.get("metadata", {}).get("auto_calculated")):
                    gold_auto_updated = True
                    break
            
            details = f"Net worth: ₹{response['total_net_worth']:.0f}"
            if gold_auto_updated:
                details += ", Gold auto-updated ✓"
            
            return self.log_test("Dashboard with Gold Updates", True, details)
        else:
            return self.log_test("Dashboard with Gold Updates", False, f"Response: {response}")

    def test_delete_milestone(self, milestone_id: str) -> bool:
        """Test deleting a milestone"""
        success, response = self.make_request("DELETE", f"milestones/{milestone_id}", 
                                            expected_status=200, auth_required=True)
        
        if success and "message" in response:
            return self.log_test("Delete Milestone", True, "Milestone deleted successfully")
        else:
            return self.log_test("Delete Milestone", False, f"Response: {response}")

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
        for milestone_id in self.created_milestones:
            self.test_delete_milestone(milestone_id)
        for asset_id in self.created_assets:
            self.test_delete_asset(asset_id)

    def run_all_tests(self) -> int:
        """Run all tests"""
        print(f"🚀 Starting Enhanced Wealth Tracker API Tests")
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

        # Gold Price API Tests
        print(f"\n🥇 Gold Price API Tests")
        self.test_gold_prices_api()
        self.test_gold_value_calculation()

        # Asset Management Tests
        print(f"\n📊 Asset Management Tests")
        
        # Test different asset types including gold
        self.test_asset_types()
        
        # Test gold asset with auto-calculation
        gold_asset_id = self.test_create_gold_asset()
        
        # Test SIP asset creation and management
        print(f"\n💰 SIP Asset Management Tests")
        sip_asset_id = self.test_create_sip_asset()
        if sip_asset_id:
            self.test_update_sip_asset(sip_asset_id)
        
        # Test CRUD operations with first created asset
        if self.created_assets:
            first_asset = self.created_assets[0]
            self.test_get_single_asset(first_asset)
            self.test_update_asset(first_asset)
        
        self.test_get_assets()

        # Milestone Tests
        print(f"\n🎯 Milestone Management Tests")
        self.test_create_milestone()
        self.test_get_milestones()

        # Projection Tests
        print(f"\n📈 Net Worth Projection Tests")
        self.test_projections_calculation()
        
        # Enhanced SIP Projection Tests
        print(f"\n📈 Enhanced SIP Projection Tests")
        self.test_sip_projections_calculation()
        self.test_step_up_sip_calculation()

        # REVOLUTIONARY ADVANCED ANALYTICS TESTS
        print(f"\n🧠 REVOLUTIONARY ADVANCED ANALYTICS TESTS")
        self.test_advanced_analytics_monte_carlo()
        self.test_advanced_analytics_health_score()
        self.test_advanced_analytics_performance()
        self.test_advanced_analytics_tax_optimization()
        self.test_advanced_analytics_comprehensive_report()

        # Enhanced Dashboard Tests
        print(f"\n📊 Enhanced Dashboard Tests")
        self.test_dashboard_with_gold_updates()

        # Cleanup
        self.cleanup_test_data()

        # Results
        print("\n" + "=" * 60)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            print("✅ Gold Price API integration working")
            print("✅ Auto-calculation for gold assets working")
            print("✅ SIP asset creation and management working")
            print("✅ SIP projections with step-up calculations working")
            print("✅ Enhanced Net Worth Projections working")
            print("✅ Milestone management working")
            print("✅ Enhanced dashboard working")
            return 0
        else:
            print(f"⚠️  {self.tests_run - self.tests_passed} tests failed")
            return 1

def main():
    tester = WealthTrackerAPITester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())