import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class for the application"""
    
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Groq AI configuration
    GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
    GROQ_CHAT_MODEL = os.environ.get('GROQ_CHAT_MODEL', 'llama-3.3-70b-versatile')
    GROQ_VISION_MODEL = os.environ.get(
        'GROQ_VISION_MODEL',
        'meta-llama/llama-4-scout-17b-16e-instruct',
    )
    
    # Pinecone vector database configuration
    PINECONE_API_KEY = os.environ.get('PINECONE_API_KEY')
    PINECONE_INDEX_NAME = os.environ.get('PINECONE_INDEX_NAME', 'smartqrmenu-menus')
    PINECONE_CLOUD = os.environ.get('PINECONE_CLOUD', 'aws')
    PINECONE_REGION = os.environ.get('PINECONE_REGION', 'us-east-1')
    PINECONE_EMBED_MODEL = os.environ.get('PINECONE_EMBED_MODEL', 'multilingual-e5-large')
    PINECONE_EMBED_DIMENSION = int(os.environ.get('PINECONE_EMBED_DIMENSION', '1024'))
    RAG_TOP_K = int(os.environ.get('RAG_TOP_K', '8'))
    
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
        
        if not Config.GROQ_API_KEY:
            config_issues.append("GROQ_API_KEY not set. AI chat features will be disabled.")
        
        if not Config.PINECONE_API_KEY:
            config_issues.append(
                "PINECONE_API_KEY not set. Menu vector search will be disabled."
            )
        
        # Check Firebase config
        firebase_required = [
            'FIREBASE_API_KEY', 'FIREBASE_AUTH_DOMAIN', 'FIREBASE_PROJECT_ID',
            'FIREBASE_STORAGE_BUCKET', 'FIREBASE_MESSAGING_SENDER_ID', 'FIREBASE_APP_ID'
        ]
        
        missing_firebase = [key for key in firebase_required if not getattr(Config, key)]
        if missing_firebase:
            config_issues.append(
                f"Firebase configuration incomplete. Missing: {', '.join(missing_firebase)}"
            )
        
        if config_issues:
            for issue in config_issues:
                print(f"⚠️ {issue}")
            return False
        
        return True
