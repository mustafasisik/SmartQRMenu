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

3. **Set up AI (Groq + Pinecone):**
   - Groq API key: [console.groq.com](https://console.groq.com/)
   - Pinecone API key: [app.pinecone.io](https://app.pinecone.io/)
   - Copy `.env.example` to `.env` and fill in `GROQ_API_KEY` and `PINECONE_API_KEY`

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
- `GROQ_API_KEY`: Groq API key (chat + menu image analysis)
- `PINECONE_API_KEY`: Pinecone API key (menu vector search / RAG)

### Optional AI tuning
- `GROQ_CHAT_MODEL`: Default `llama-3.3-70b-versatile`
- `GROQ_VISION_MODEL`: Default `meta-llama/llama-4-scout-17b-16e-instruct`
- `PINECONE_INDEX_NAME`: Default `smartqrmenu-menus`
- `RAG_TOP_K`: Number of menu chunks retrieved per question (default `8`)

### Optional
- `SECRET_KEY`: Flask secret key (auto-generated if not set)
- `FIREBASE_SERVICE_ACCOUNT_PATH`: Path to Firebase service account key file (for admin operations)
- `FIRESTORE_DATABASE_ID`: Your Firestore database ID (defaults to FIREBASE_PROJECT_ID)
- `FIRESTORE_LOCATION`: Your Firestore database location (defaults to us-central1)

## File Structure

- `config.py` - Configuration management
- `groq_service.py` - Groq LLM integration
- `menu_vector_store.py` - Pinecone menu indexing & search
- `rag_service.py` - RAG orchestration (Pinecone → Groq)
- `app.py` - Main Flask application
- `restaurant.json` - Restaurant data

## AI Features

The AI garson (RAG) searches the menu in Pinecone, then Groq answers about:
- Restaurant location and contact info
- Menu items and prices
- Chef information and experience
- Customer reviews and ratings
- Working hours and features
- Awards and specialties

## Troubleshooting

### AI Service Not Available
- Check if `.env` file exists
- Verify `GROQ_API_KEY` and `PINECONE_API_KEY` are set correctly
- Re-index menu: `POST /api/menu/index/<restaurant_slug>` with `{"force": true}`
- Ensure internet connection for API calls

### Import Errors
- Activate virtual environment: `source venv/bin/activate`
- Reinstall dependencies: `pip install -r requirements.txt`

## Deployment

### Render.com (önerilen — ücretsiz, Blaze gerekmez)

**[DEPLOY_RENDER.md](DEPLOY_RENDER.md)**

1. GitHub’a push
2. Render → Blueprint → `render.yaml`
3. Environment: `render.env.example` içeriğini dashboard’a yapıştırın
4. Firebase Auth → Authorized domains → Render URL

### Firebase Hosting + Cloud Run (alternatif)

GCP faturalandırma gerekir: **[DEPLOY_FIREBASE.md](DEPLOY_FIREBASE.md)**

### Diğer

- `Dockerfile` — container deploy
