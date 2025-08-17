import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class for the application"""
    
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Gemini AI configuration
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    
    # Restaurant data file
    RESTAURANT_DATA_FILE = 'restaurant.json'
    
    # Firebase configuration
    FIREBASE_API_KEY = os.environ.get('FIREBASE_API_KEY')
    FIREBASE_AUTH_DOMAIN = os.environ.get('FIREBASE_AUTH_DOMAIN')
    FIREBASE_PROJECT_ID = os.environ.get('FIREBASE_PROJECT_ID')
    FIREBASE_STORAGE_BUCKET = os.environ.get('FIREBASE_STORAGE_BUCKET')
    FIREBASE_MESSAGING_SENDER_ID = os.environ.get('FIREBASE_MESSAGING_SENDER_ID')
    FIREBASE_APP_ID = os.environ.get('FIREBASE_APP_ID')
    FIREBASE_SERVICE_ACCOUNT_PATH = os.environ.get('FIREBASE_SERVICE_ACCOUNT_PATH')
    
    # Firestore configuration
    FIRESTORE_DATABASE_ID = os.environ.get('FIRESTORE_DATABASE_ID') or FIREBASE_PROJECT_ID
    FIRESTORE_LOCATION = os.environ.get('FIRESTORE_LOCATION', 'us-central1')
    
    @staticmethod
    def validate_config():
        """Validate that required configuration is present"""
        config_issues = []
        
        if not Config.GEMINI_API_KEY:
            config_issues.append("GEMINI_API_KEY not set. AI features will be disabled.")
        
        # Check Firebase config
        firebase_required = [
            'FIREBASE_API_KEY', 'FIREBASE_AUTH_DOMAIN', 'FIREBASE_PROJECT_ID',
            'FIREBASE_STORAGE_BUCKET', 'FIREBASE_MESSAGING_SENDER_ID', 'FIREBASE_APP_ID'
        ]
        
        missing_firebase = [key for key in firebase_required if not getattr(Config, key)]
        if missing_firebase:
            config_issues.append(f"Firebase configuration incomplete. Missing: {', '.join(missing_firebase)}")
        
        if config_issues:
            for issue in config_issues:
                print(f"⚠️ {issue}")
            return False
        
        return True
