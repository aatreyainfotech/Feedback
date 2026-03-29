import requests
import sys
import json
from datetime import datetime

class TempleBackendTester:
    def __init__(self, base_url="https://temple-feedback-1.preview.emergentagent.com"):
        self.base_url = base_url
        self.admin_token = None
        self.officer_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.created_temple_id = None
        self.created_officer_id = None
        self.created_feedback_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        if headers:
            test_headers.update(headers)

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return True, response.json()
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    print(f"   Response: {response.text}")
                except:
                    pass
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_admin_login(self):
        """Test admin login"""
        success, response = self.run_test(
            "Admin Login",
            "POST",
            "auth/admin/login",
            200,
            data={"email": "admin@temple.com", "password": "admin123"}
        )
        if success and 'token' in response:
            self.admin_token = response['token']
            print(f"   Admin token obtained: {self.admin_token[:20]}...")
            return True
        return False

    def test_get_temples(self):
        """Test getting temples list"""
        success, response = self.run_test(
            "Get Temples",
            "GET",
            "temples",
            200
        )
        if success:
            print(f"   Found {len(response)} temples")
            return True
        return False

    def test_create_temple(self):
        """Test creating a temple"""
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        temple_data = {
            "name": "Test Temple",
            "location": "Test Location"
        }
        success, response = self.run_test(
            "Create Temple",
            "POST",
            "temples",
            200,
            data=temple_data,
            headers=headers
        )
        if success and 'id' in response:
            self.created_temple_id = response['id']
            print(f"   Created temple ID: {self.created_temple_id}")
            return True
        return False

    def test_create_officer(self):
        """Test creating an officer"""
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        officer_data = {
            "name": "Test Officer",
            "email": "test.officer@temple.com",
            "password": "testpass123",
            "temple_id": self.created_temple_id
        }
        success, response = self.run_test(
            "Create Officer",
            "POST",
            "officers",
            200,
            data=officer_data,
            headers=headers
        )
        if success and 'id' in response:
            self.created_officer_id = response['id']
            print(f"   Created officer ID: {self.created_officer_id}")
            return True
        return False

    def test_officer_login(self):
        """Test officer login"""
        success, response = self.run_test(
            "Officer Login",
            "POST",
            "auth/officer/login",
            200,
            data={"email": "test.officer@temple.com", "password": "testpass123"}
        )
        if success and 'token' in response:
            self.officer_token = response['token']
            print(f"   Officer token obtained: {self.officer_token[:20]}...")
            return True
        return False

    def test_get_officers(self):
        """Test getting officers list"""
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        success, response = self.run_test(
            "Get Officers",
            "GET",
            "officers",
            200,
            headers=headers
        )
        if success:
            print(f"   Found {len(response)} officers")
            return True
        return False

    def test_create_feedback(self):
        """Test creating feedback"""
        feedback_data = {
            "temple_id": self.created_temple_id,
            "user_mobile": "+919876543210",
            "user_name": "Test Devotee",
            "service": "Seva",
            "rating": 4,
            "message": "Test feedback message"
        }
        success, response = self.run_test(
            "Create Feedback",
            "POST",
            "feedback",
            200,
            data=feedback_data
        )
        if success and 'id' in response:
            self.created_feedback_id = response['id']
            print(f"   Created feedback ID: {self.created_feedback_id}")
            return True
        return False

    def test_get_feedback(self):
        """Test getting all feedback"""
        success, response = self.run_test(
            "Get All Feedback",
            "GET",
            "feedback",
            200
        )
        if success:
            print(f"   Found {len(response)} feedback entries")
            return True
        return False

    def test_get_officer_feedback(self):
        """Test getting officer-specific feedback"""
        headers = {"Authorization": f"Bearer {self.officer_token}"}
        success, response = self.run_test(
            "Get Officer Feedback",
            "GET",
            "feedback/officer",
            200,
            headers=headers
        )
        if success:
            print(f"   Found {len(response)} feedback entries for officer")
            return True
        return False

    def test_update_feedback_status(self):
        """Test updating feedback status"""
        headers = {"Authorization": f"Bearer {self.officer_token}"}
        update_data = {
            "status": "In Progress",
            "officer_notes": "Working on this issue"
        }
        success, response = self.run_test(
            "Update Feedback Status",
            "PUT",
            f"feedback/{self.created_feedback_id}/status",
            200,
            data=update_data,
            headers=headers
        )
        return success

    def test_dashboard_stats(self):
        """Test admin dashboard stats"""
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        success, response = self.run_test(
            "Dashboard Stats",
            "GET",
            "dashboard/stats",
            200,
            headers=headers
        )
        if success:
            print(f"   Stats: {json.dumps(response, indent=2)}")
            return True
        return False

    def test_officer_stats(self):
        """Test officer dashboard stats"""
        headers = {"Authorization": f"Bearer {self.officer_token}"}
        success, response = self.run_test(
            "Officer Stats",
            "GET",
            "dashboard/officer-stats",
            200,
            headers=headers
        )
        if success:
            print(f"   Officer Stats: {json.dumps(response, indent=2)}")
            return True
        return False

    def test_whatsapp_logs(self):
        """Test WhatsApp logs"""
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        success, response = self.run_test(
            "WhatsApp Logs",
            "GET",
            "whatsapp/logs",
            200,
            headers=headers
        )
        if success:
            print(f"   Found {len(response)} WhatsApp logs")
            return True
        return False

    def test_display_live_feed(self):
        """Test display screen live feed"""
        success, response = self.run_test(
            "Display Live Feed",
            "GET",
            "display/live-feed",
            200
        )
        if success:
            print(f"   Found {len(response)} items in live feed")
            return True
        return False

    def test_send_otp(self):
        """Test OTP sending (mock)"""
        success, response = self.run_test(
            "Send OTP",
            "POST",
            "auth/send-otp",
            200,
            data={"mobile": "+919876543210"}
        )
        if success:
            print(f"   OTP response: {response}")
            return True
        return False

    def test_verify_otp(self):
        """Test OTP verification (mock)"""
        success, response = self.run_test(
            "Verify OTP",
            "POST",
            "auth/verify-otp",
            200,
            data={"mobile": "+919876543210", "otp": "123456"}
        )
        return success

    def cleanup(self):
        """Clean up created test data"""
        print("\n🧹 Cleaning up test data...")
        
        # Delete created officer
        if self.created_officer_id and self.admin_token:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            self.run_test(
                "Delete Test Officer",
                "DELETE",
                f"officers/{self.created_officer_id}",
                200,
                headers=headers
            )
        
        # Delete created temple
        if self.created_temple_id and self.admin_token:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            self.run_test(
                "Delete Test Temple",
                "DELETE",
                f"temples/{self.created_temple_id}",
                200,
                headers=headers
            )

def main():
    print("🏛️ Temple Feedback Management System - Backend API Testing")
    print("=" * 60)
    
    tester = TempleBackendTester()
    
    # Test sequence
    tests = [
        ("Admin Authentication", tester.test_admin_login),
        ("Get Temples", tester.test_get_temples),
        ("Create Temple", tester.test_create_temple),
        ("Create Officer", tester.test_create_officer),
        ("Officer Authentication", tester.test_officer_login),
        ("Get Officers", tester.test_get_officers),
        ("Create Feedback", tester.test_create_feedback),
        ("Get All Feedback", tester.test_get_feedback),
        ("Get Officer Feedback", tester.test_get_officer_feedback),
        ("Update Feedback Status", tester.test_update_feedback_status),
        ("Dashboard Stats", tester.test_dashboard_stats),
        ("Officer Stats", tester.test_officer_stats),
        ("WhatsApp Logs", tester.test_whatsapp_logs),
        ("Display Live Feed", tester.test_display_live_feed),
        ("Send OTP (Mock)", tester.test_send_otp),
        ("Verify OTP (Mock)", tester.test_verify_otp),
    ]
    
    # Run all tests
    for test_name, test_func in tests:
        try:
            test_func()
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
    
    # Cleanup
    tester.cleanup()
    
    # Print results
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {tester.tests_passed}/{tester.tests_run} tests passed")
    success_rate = (tester.tests_passed / tester.tests_run * 100) if tester.tests_run > 0 else 0
    print(f"📈 Success Rate: {success_rate:.1f}%")
    
    if success_rate >= 80:
        print("✅ Backend API testing completed successfully!")
        return 0
    else:
        print("❌ Backend API testing failed - multiple issues found")
        return 1

if __name__ == "__main__":
    sys.exit(main())