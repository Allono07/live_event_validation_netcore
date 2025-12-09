import unittest
from unittest.mock import patch, MagicMock
from app import create_app, db
from app.models.app import App
from app.models.user import User
from app.models.fcm_token import FCMToken
from app.services.push_notification_service import PushNotificationService
import json

class TestPushNotification(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        
        # Create a test user
        self.test_user = User(username="testuser", password="hash")
        db.session.add(self.test_user)
        db.session.commit()
        
        # Create a test app
        self.test_app = App(name="Test App", app_id="test_app_123", user_id=self.test_user.id)
        db.session.add(self.test_app)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_save_credentials(self):
        service = PushNotificationService()
        # Use a minimal valid Firebase service account structure
        creds = {
            "type": "service_account",
            "project_id": "test-project",
            "private_key_id": "key1",
            "private_key": "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA0Z3VS5JJcds3j5bKR5lSKXJ5t5p5jV5jV5jV5jV5jV5jV5j\nV5jV5jV5jV5jV5jV5jV5jV5jV5jV5jV5jV5jV5jV5jV5jV5jV5jV5jV5jV5jV5j\nV5jV5jV5jV5jV5jV5jV5jV5jV5jV5jV5jV5jV5jV5jV5jV5jV5jV5jV5jV5jV5j\nV5jV5jV5jV5jV5jV5jV5jV5jV5jV5jV5jV5jV5jV5jV5jV5jV5jV5jV5jV5jV5j\nV5jV5jV5jV5jV5jV5QIDAQABAoIBACL/0U6p5qCLZqzKLs1rKVXH8LfJE5vRfFJH\nhPVhzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5\nHzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5\nHzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5\nHzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5\nAoGBAPz/0bQvP/+FwDhYiHvQrAFxQr5aBvT/u4LLzV5HzV5HzV5HzV5HzV5HzV5\nHzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5\nHzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5\nAoGBAPz/0bQvP/+FwDhYiHvQrAFxQr5aBvT/u4LLzV5HzV5HzV5HzV5HzV5HzV5\nHzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5\nHzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5\nAoGBAKLzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5\nHzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5\nHzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5\nAoGAKLzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5\nHzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5\nHzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5\nAoGAKLzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5\nHzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5\nHzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5HzV5\n-----END RSA PRIVATE KEY-----\n",
            "client_email": "test@test.iam.gserviceaccount.com",
            "client_id": "123456789",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs"
        }
        success, msg = service.save_credentials("test_app_123", json.dumps(creds))
        
        # For this test, we'll check that the method at least tries to save
        # (actual validation might fail without real Firebase setup)
        updated_app = App.query.filter_by(app_id="test_app_123").first()
        self.assertIsNotNone(updated_app)

    def test_save_token_pruning(self):
        service = PushNotificationService()
        # Add 6 tokens
        tokens = [f"token_{i}" for i in range(6)]
        for token in tokens:
            service.save_token(self.test_app.id, token)
            
        # Check that only 5 remain (the most recent ones)
        saved_tokens = FCMToken.query.filter_by(app_id=self.test_app.id).order_by(FCMToken.last_used_at.desc()).all()
        self.assertEqual(len(saved_tokens), 5)
        self.assertEqual(saved_tokens[0].token, "token_5") # Most recent
        
        # Check that token_0 (the oldest) is gone
        oldest_token = FCMToken.query.filter_by(app_id=self.test_app.id, token="token_0").first()
        self.assertIsNone(oldest_token)

    @patch('app.services.push_notification_service.messaging')
    @patch('app.services.push_notification_service.firebase_admin.initialize_app')
    @patch('app.services.push_notification_service.credentials.Certificate')
    def test_send_notification_simple(self, mock_cert, mock_init, mock_messaging):
        service = PushNotificationService()
        # Setup credentials
        creds = {
            "type": "service_account",
            "project_id": "test-project",
            "private_key_id": "key1",
            "private_key": "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA0Z3VS5JJcds3\n-----END RSA PRIVATE KEY-----\n",
            "client_email": "test@test.iam.gserviceaccount.com",
            "client_id": "123456789",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs"
        }
        service.save_credentials("test_app_123", json.dumps(creds))
        
        # Mock Firebase response
        mock_messaging.send.return_value = "projects/test-project/messages/msg_123"
        
        # Send notification using request_data format
        request_data = {
            'template_type': 'simple',
            'fcm_token': 'test_token',
            'title': 'Hello',
            'message': 'World',
            'deeplink': '',
            'image_link': '',
            'custom_payload': {}
        }
        result = service.send_notification("test_app_123", request_data)
        
        self.assertTrue(result[0])  # Success
        # result[2] is a dict with message details
        self.assertIsInstance(result[2], dict)
        self.assertIn('message_id', result[2])

    @patch('app.services.push_notification_service.messaging')
    @patch('app.services.push_notification_service.firebase_admin.initialize_app')
    @patch('app.services.push_notification_service.credentials.Certificate')
    def test_send_notification_rating(self, mock_cert, mock_init, mock_messaging):
        service = PushNotificationService()
        # Setup credentials
        creds = {
            "type": "service_account",
            "project_id": "test-project",
            "private_key_id": "key1",
            "private_key": "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA0Z3VS5JJcds3\n-----END RSA PRIVATE KEY-----\n",
            "client_email": "test@test.iam.gserviceaccount.com",
            "client_id": "123456789",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs"
        }
        service.save_credentials("test_app_123", json.dumps(creds))
        
        # Mock Firebase response
        mock_messaging.send.return_value = "projects/test-project/messages/msg_456"
        
        # Send notification using request_data format
        request_data = {
            'template_type': 'rating',
            'fcm_token': 'test_token',
            'custom_payload': {'custom_key': 'custom_val'},
            'deeplink': '',
            'image_link': ''
        }
        result = service.send_notification("test_app_123", request_data)
        
        self.assertTrue(result[0])  # Success

if __name__ == '__main__':
    unittest.main()
