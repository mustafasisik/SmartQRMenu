# SmartQRMenu Setup Guide

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up Firebase Authentication:**
   - Go to [Firebase Console](https://console.firebase.google.com/)
   - Create a new project or select existing one
   - Enable Authentication (Email/Password + Google)
   - Get your Firebase config from Project Settings
   - Create `.env` file in project root with Firebase config

3. **Set up Gemini AI (optional but recommended):**
   - Get API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Add to `.env` file: `GEMINI_API_KEY=your_key_here`

4. **Run the application:**
   ```bash
   python app.py
   ```

## Environment Variables

### Required for Authentication
- `FIREBASE_API_KEY`: Your Firebase API key
- `FIREBASE_AUTH_DOMAIN`: Your Firebase auth domain (project.firebaseapp.com)
- `FIREBASE_PROJECT_ID`: Your Firebase project ID
- `FIREBASE_STORAGE_BUCKET`: Your Firebase storage bucket
- `FIREBASE_MESSAGING_SENDER_ID`: Your Firebase messaging sender ID
- `FIREBASE_APP_ID`: Your Firebase app ID

### Required for AI Features
- `GEMINI_API_KEY`: Your Google Gemini API key

### Optional
- `SECRET_KEY`: Flask secret key (auto-generated if not set)
- `FIREBASE_SERVICE_ACCOUNT_PATH`: Path to Firebase service account key file (for admin operations)
- `FIRESTORE_DATABASE_ID`: Your Firestore database ID (defaults to FIREBASE_PROJECT_ID)
- `FIRESTORE_LOCATION`: Your Firestore database location (defaults to us-central1)

## File Structure

- `config.py` - Configuration management
- `gemini_service.py` - Gemini AI integration
- `app.py` - Main Flask application
- `restaurant.json` - Restaurant data

## AI Features

The Gemini AI chatbot can answer questions about:
- Restaurant location and contact info
- Menu items and prices
- Chef information and experience
- Customer reviews and ratings
- Working hours and features
- Awards and specialties

## Troubleshooting

### AI Service Not Available
- Check if `.env` file exists
- Verify `GEMINI_API_KEY` is set correctly
- Ensure internet connection for API calls

### Import Errors
- Activate virtual environment: `source venv/bin/activate`
- Reinstall dependencies: `pip install -r requirements.txt`

## Deployment

The application includes:
- `render.yaml` for Render.com
- `Procfile` for Heroku/other platforms
- `requirements.txt` with compatible versions
