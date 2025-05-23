import sys
import os

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Now imports should work
from flask_testing import TestCase
import json
import unittest
from werkzeug.security import check_password_hash

from backend.models import User
from backend.app import create_app, db

class AuthTestCase(TestCase):
    """Test suite for authentication features."""
    
    def create_app(self):
        """Create test app with isolated test configuration."""
        return create_app('testing')
    
    def setUp(self):
        """Set up fresh database for each test."""
        db.create_all()
    
    def tearDown(self):
        """Clean up after each test."""
        db.session.remove()
        db.drop_all()
    
    def create_test_user(self, username='testuser', email='test@example.com', password='TestPassword123'):
        """Helper method to create test users."""
        response = self.client.post(
            '/auth/register',
            data=json.dumps({
                'username': username,
                'email': email,
                'password': password
            }),
            content_type='application/json'
        )
        return response
    
    def login_user(self, identifier='testuser', password='TestPassword123'):
        """Helper method to login users."""
        return self.client.post(
            '/auth/login',
            data=json.dumps({
                'identifier': identifier,
                'password': password
            }),
            content_type='application/json'
        )
    
    def get_response_data(self, response):
        """Helper to decode JSON response."""
        return json.loads(response.data.decode())
    
    # === REGISTRATION TESTS ===
    
    def test_register_success(self):
        """Test successful user registration."""
        response = self.create_test_user()
        
        # Check response
        self.assertEqual(response.status_code, 201)
        data = self.get_response_data(response)
        self.assertEqual(data['message'], 'User registered successfully')
        
        # Verify user created in database
        user = User.query.filter_by(username='testuser').first()
        self.assertIsNotNone(user)
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.current_streak, 0)
        self.assertEqual(user.longest_streak, 0)
    
    def test_register_duplicate_username(self):
        """Test registration with duplicate username."""
        # Create first user
        self.create_test_user()
        
        # Try to register with same username
        response = self.create_test_user(email='different@example.com')
        
        self.assertEqual(response.status_code, 409)
        data = self.get_response_data(response)
        self.assertEqual(data['error'], 'Username already exists')
    
    def test_register_duplicate_email(self):
        """Test registration with duplicate email."""
        # Create first user
        self.create_test_user()
        
        # Try to register with same email but different username
        response = self.create_test_user(username='differentuser')
        
        self.assertEqual(response.status_code, 409)
        data = self.get_response_data(response)
        self.assertEqual(data['error'], 'Email already exists')
    
    def test_register_missing_fields(self):
        """Test registration with missing required fields."""
        test_cases = [
            ({}, 'No data provided'),
            ({'username': 'user'}, 'Missing required fields'),
            ({'email': 'test@example.com'}, 'Missing required fields'),
            ({'password': 'pass123'}, 'Missing required fields'),
        ]
        
        for data, expected_error_type in test_cases:
            with self.subTest(data=data):
                response = self.client.post(
                    '/auth/register',
                    data=json.dumps(data),
                    content_type='application/json'
                )
                self.assertEqual(response.status_code, 400)
    
    def test_register_invalid_data(self):
        """Test registration with invalid data formats."""
        test_cases = [
            {
                'username': 'ab',  # Too short
                'email': 'test@example.com',
                'password': 'ValidPass123'
            },
            {
                'username': 'validuser',
                'email': 'invalid-email',  # Invalid email format
                'password': 'ValidPass123'
            },
            {
                'username': 'validuser',
                'email': 'test@example.com',
                'password': '123'  # Too short
            },
            {
                'username': '',  # Empty username
                'email': 'test@example.com',
                'password': 'ValidPass123'
            },
        ]
        
        for data in test_cases:
            with self.subTest(data=data):
                response = self.client.post(
                    '/auth/register',
                    data=json.dumps(data),
                    content_type='application/json'
                )
                self.assertEqual(response.status_code, 400)
    
    def test_register_no_json_data(self):
        """Test registration with no JSON data."""
        response = self.client.post('/auth/register')
        self.assertIn(response.status_code, [400, 415])
    
    def test_password_hashing(self):
        """Test that passwords are properly hashed."""
        password = 'TestPassword123'
        self.create_test_user(password=password)
        
        user = User.query.filter_by(username='testuser').first()
        
        # Password should be hashed, not stored in plain text
        self.assertNotEqual(user.password, password)
        self.assertTrue(len(user.password) > 50)  # Hashed passwords are long
        
        # Verify the hash is valid
        self.assertTrue(check_password_hash(user.password, password))
    
    # === LOGIN TESTS ===
    
    def test_login_success_username(self):
        """Test successful login with username."""
        # Create user
        self.create_test_user()
        
        # Login
        response = self.login_user()
        
        self.assertEqual(response.status_code, 200)
        data = self.get_response_data(response)
        self.assertEqual(data['message'], 'Logged in successfully')
        
        # Check user data is returned
        self.assertIn('user', data)
        self.assertEqual(data['user']['username'], 'testuser')
        self.assertEqual(data['user']['email'], 'test@example.com')
        self.assertNotIn('password', data['user'])  # Password should not be returned
    
    def test_login_success_email(self):
        """Test successful login with email."""
        # Create user
        self.create_test_user()
        
        # Login with email
        response = self.login_user(identifier='test@example.com')
        
        self.assertEqual(response.status_code, 200)
        data = self.get_response_data(response)
        self.assertEqual(data['message'], 'Logged in successfully')
        self.assertEqual(data['user']['username'], 'testuser')
    
    def test_login_invalid_username(self):
        """Test login with non-existent username."""
        response = self.login_user(identifier='nonexistentuser')
        
        self.assertEqual(response.status_code, 401)
        data = self.get_response_data(response)
        self.assertEqual(data['error'], 'Invalid credentials')
    
    def test_login_wrong_password(self):
        """Test login with correct username but wrong password."""
        # Create user
        self.create_test_user()
        
        # Try login with wrong password
        response = self.login_user(password='WrongPassword123')
        
        self.assertEqual(response.status_code, 401)
        data = self.get_response_data(response)
        self.assertEqual(data['error'], 'Invalid credentials')
    
    def test_login_missing_fields(self):
        """Test login with missing fields."""
        test_cases = [
            {},  # No data
            {'identifier': 'user'},  # Missing password
            {'password': 'pass'},  # Missing identifier
        ]
        
        for data in test_cases:
            with self.subTest(data=data):
                response = self.client.post(
                    '/auth/login',
                    data=json.dumps(data),
                    content_type='application/json'
                )
                self.assertEqual(response.status_code, 400)
    
    def test_login_empty_fields(self):
        """Test login with empty fields."""
        test_cases = [
            {'identifier': '', 'password': 'password'},
            {'identifier': 'user', 'password': ''},
            {'identifier': '', 'password': ''},
        ]
        
        for data in test_cases:
            with self.subTest(data=data):
                response = self.client.post(
                    '/auth/login',
                    data=json.dumps(data),
                    content_type='application/json'
                )
                self.assertEqual(response.status_code, 400)
    
    def test_login_no_json_data(self):
        """Test login with no JSON data."""
        response = self.client.post('/auth/login')
        self.assertIn(response.status_code, [400, 415])
    
    # === LOGOUT TESTS ===
    
    def test_logout_success(self):
        """Test successful logout after login."""
        # Create and login user
        self.create_test_user()
        self.login_user()
        
        # Logout
        response = self.client.post('/auth/logout')
        
        self.assertEqual(response.status_code, 200)
        data = self.get_response_data(response)
        self.assertEqual(data['message'], 'Logged out successfully')
    
    def test_logout_without_login(self):
        """Test logout without being logged in."""
        response = self.client.post('/auth/logout')
        
        # Should require login (depends on your @login_required implementation)
        self.assertIn(response.status_code, [302, 401])
    
    # === INTEGRATION TESTS ===
    
    def test_login_logout_flow(self):
        """Test complete login-logout flow."""
        # Register
        register_response = self.create_test_user()
        self.assertEqual(register_response.status_code, 201)
        
        # Login
        login_response = self.login_user()
        self.assertEqual(login_response.status_code, 200)
        
        # Logout
        logout_response = self.client.post('/auth/logout')
        self.assertEqual(logout_response.status_code, 200)
        
        # Try to logout again (should fail)
        logout_response2 = self.client.post('/auth/logout')
        self.assertIn(logout_response2.status_code, [302, 401])
    
    def test_multiple_users(self):
        """Test creating and managing multiple users."""
        users = [
            ('user1', 'user1@example.com', 'Password123'),
            ('user2', 'user2@example.com', 'Password456'),
            ('user3', 'user3@example.com', 'Password789'),
        ]
        
        # Create all users
        for username, email, password in users:
            response = self.create_test_user(username, email, password)
            self.assertEqual(response.status_code, 201)
        
        # Verify all users exist in database
        for username, email, password in users:
            user = User.query.filter_by(username=username).first()
            self.assertIsNotNone(user)
            self.assertEqual(user.email, email)
        
        # Test login for each user
        for username, email, password in users:
            response = self.login_user(username, password)
            self.assertEqual(response.status_code, 200)
    
    def test_user_streak_initialization(self):
        """Test that new users have correct initial streak values."""
        self.create_test_user()
        
        user = User.query.filter_by(username='testuser').first()
        self.assertEqual(user.current_streak, 0)
        self.assertEqual(user.longest_streak, 0)
        self.assertIsNotNone(user.last_activity_date)  # Should be set during registration
    
    # === SECURITY TESTS ===
    
    def test_password_not_in_response(self):
        """Test that password is never included in API responses."""
        # Register
        register_response = self.create_test_user()
        register_data = self.get_response_data(register_response)
        self.assertNotIn('password', str(register_data))
        
        # Login
        login_response = self.login_user()
        login_data = self.get_response_data(login_response)
        self.assertNotIn('password', str(login_data))
    
    def test_sql_injection_protection(self):
        """Test protection against SQL injection attempts."""
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "admin'--",
            "' OR '1'='1",
            "' UNION SELECT * FROM users --",
        ]
        
        for malicious_input in malicious_inputs:
            with self.subTest(input=malicious_input):
                response = self.login_user(identifier=malicious_input, password='password')
                # Should not cause server error (500), should return 401
                self.assertIn(response.status_code, [400, 401])

if __name__ == '__main__':
    unittest.main()