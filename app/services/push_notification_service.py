"""Push Notification Service."""
import json
import logging
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, messaging
from app.models.app import App
from app.models.fcm_token import FCMToken
from app.models.firebase_credential import FirebaseCredential
from config.database import db

logger = logging.getLogger(__name__)

class PushNotificationService:
    """Service for handling push notifications via FCM."""

    def validate_credentials(self, credentials_json):
        """Validate Firebase service account credentials."""
        try:
            if isinstance(credentials_json, str):
                cred_dict = json.loads(credentials_json)
            else:
                cred_dict = credentials_json
                
            # Basic validation of structure
            required_fields = ['project_id', 'private_key', 'client_email']
            for field in required_fields:
                if field not in cred_dict:
                    return False, f"Missing required field: {field}"
            
            # Try to create a credential object to verify
            credentials.Certificate(cred_dict)
            return True, "Credentials are valid"
        except Exception as e:
            return False, f"Invalid credentials: {str(e)}"

    def save_credentials(self, app_id, credentials_json):
        """Save Firebase credentials to the app."""
        app = App.query.filter_by(app_id=app_id).first()
        if not app:
            return False, "App not found"
        
        valid, msg = self.validate_credentials(credentials_json)
        if not valid:
            return False, msg
            
        # Check if credentials already exist
        existing = FirebaseCredential.query.filter_by(app_id=app.id).first()
        if existing:
            existing.credentials_json = credentials_json
            existing.updated_at = datetime.utcnow()
        else:
            new_cred = FirebaseCredential(app_id=app.id, credentials_json=credentials_json)
            db.session.add(new_cred)
        
        db.session.commit()
        return True, "Credentials saved successfully"

    def get_firebase_app(self, app):
        """Get or initialize Firebase app instance for the specific app."""
        # Get credentials from separate table
        firebase_cred = FirebaseCredential.query.filter_by(app_id=app.id).first()
        if not firebase_cred:
            return None
            
        app_name = f"app_{app.app_id}"
        try:
            return firebase_admin.get_app(app_name)
        except ValueError:
            # App not initialized, initialize it
            try:
                cred_dict = json.loads(firebase_cred.credentials_json)
                cred = credentials.Certificate(cred_dict)
                return firebase_admin.initialize_app(cred, name=app_name)
            except Exception as e:
                logger.error(f"Failed to initialize Firebase app for {app.app_id}: {e}")
                return None

    def save_token(self, app_id_db, token):
        """Save FCM token and ensure only recent 5 are kept."""
        try:
            existing = FCMToken.query.filter_by(app_id=app_id_db, token=token).first()
            if existing:
                existing.last_used_at = datetime.utcnow()
            else:
                new_token = FCMToken(app_id=app_id_db, token=token)
                db.session.add(new_token)
            
            db.session.commit()
            
            # Cleanup old tokens (keep recent 5)
            tokens = FCMToken.query.filter_by(app_id=app_id_db).order_by(FCMToken.last_used_at.desc()).all()
            if len(tokens) > 5:
                for t in tokens[5:]:
                    db.session.delete(t)
                db.session.commit()
        except Exception as e:
            logger.error(f"Error saving token: {e}")
            db.session.rollback()

    def get_recent_tokens(self, app_id_db):
        """Get recent 5 FCM tokens."""
        tokens = FCMToken.query.filter_by(app_id=app_id_db).order_by(FCMToken.last_used_at.desc()).limit(5).all()
        return [t.token for t in tokens]

    def send_notification(self, app_id, request_data):
        """Send push notification."""
        app = App.query.filter_by(app_id=app_id).first()
        if not app:
            return False, "App not found", None

        firebase_app = self.get_firebase_app(app)
        if not firebase_app:
            return False, "Firebase credentials not configured or invalid", None

        # Extract parameters
        template_type = request_data.get('template_type')
        fcm_token = request_data.get('fcm_token')
        deeplink = request_data.get('deeplink', '')
        image_link = request_data.get('image_link', '')
        title = request_data.get('title', '')
        message_text = request_data.get('message', '')
        custom_payload_str = request_data.get('custom_payload', '{}')
        
        try:
            custom_payload = json.loads(custom_payload_str) if isinstance(custom_payload_str, str) else custom_payload_str
        except:
            custom_payload = {}

        if not fcm_token:
            return False, "FCM Token is required", None

        # Save token
        self.save_token(app.id, fcm_token)

        # Construct Payload
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        trid = f"175567-591-13872-0-{timestamp}-T"
        published_date = datetime.now().isoformat()
        expiry = int((datetime.now() + timedelta(days=30)).timestamp())
        
        # Determine type
        msg_type = "Image" if image_link else "Simple"
        
        # Base data structure
        data_payload = {
            "smtSrc": "Smartech",
            "trid": trid,
            "smtCustomPayload": custom_payload
        }
        
        inner_data = {
            "actionButton": [],
            "attrParams": {},
            "carousel": [],
            "customPayload": custom_payload,
            "deeplink": deeplink,
            "expiry": expiry,
            "image": image_link,
            "message": message_text,
            "publishedDate": published_date,
            "sound": True,
            "status": "sent",
            "subtitle": "",
            "title": title,
            "trid": trid,
            "type": msg_type
        }

        smt_ui = {}

        if template_type == 'rating':
            # Override title/message for rating
            inner_data['title'] = "Rating Push Notification"
            inner_data['message'] = "Rating Push Notification"
            
            smt_ui = {
                "flid": 1,
                "lid": 1,
                "rat": {
                    "cbt": "Submit",
                    "dl": "",
                    "sc": 5,
                    "si": "https://cdna.netcoresmartech.com/14340/1680080201.png",
                    "ty": 1,
                    "ui": "https://cdna.netcoresmartech.com/14340/1680076013.png"
                }
            }
        
        data_payload['data'] = inner_data
        data_payload['smtUi'] = smt_ui

        # Convert all values to strings for FCM data payload
        # FCM data payload values must be strings
        fcm_data = {}
        for k, v in data_payload.items():
            if isinstance(v, (dict, list, bool, int, float)):
                fcm_data[k] = json.dumps(v)
            else:
                fcm_data[k] = str(v)

        # Log the payload
        logger.info("="*80)
        logger.info("COMPLETE PAYLOAD BEING SENT:")
        logger.info("="*80)
        logger.info(f"Template Type: {template_type}")
        logger.info(f"FCM Token: {fcm_token}")
        logger.info("Full Payload (JSON):")
        logger.info(json.dumps(data_payload, indent=2))
        logger.info("="*80)
        logger.info("FCM MESSAGE DATA (converted to strings):")
        logger.info("="*80)
        logger.info(json.dumps(fcm_data, indent=2))
        logger.info("="*80)

        # Send message
        try:
            message = messaging.Message(
                data=fcm_data,
                token=fcm_token,
                android=messaging.AndroidConfig(
                    priority='high',
                    # No notification field -> data-only message
                )
            )
            
            response = messaging.send(message, app=firebase_app)
            
            logger.info(f"Successfully sent notification to {fcm_token}. Message ID: {response}")
            
            return True, "Sent Successfully", {
                "message_id": response,
                "template_type": template_type,
                "device_token": fcm_token,
                "status": "Sent Successfully",
                "timestamp": published_date
            }
            
        except Exception as e:
            logger.error(f"Error sending FCM message: {e}")
            return False, str(e), None
