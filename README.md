# SmartQRMenu - Flask Application

A simple Flask web application with a modern, responsive UI.

## Features

- Clean, modern web interface
- Restaurant information page with comprehensive details
- Restaurant page with **AI garson** (Groq + Pinecone RAG menu search)
- **Firebase Authentication** with email/password and Google sign-in
- **Protected AI chatbot** - requires user authentication
- Health check API endpoint
- Hello API endpoint with POST support
- AI status monitoring and real-time feedback
- Responsive design with gradient background
- Interactive JavaScript functionality
- Tailwind CSS for modern styling
- Environment-based configuration for secure API key management
- User profile management and session handling

## Setup

### Prerequisites
- Python 3.11 or higher (recommended)
- pip (Python package installer)

### Dependency Notes
- All dependencies are configured with compatible version ranges
- Flask 3.1+ with blinker 1.9+ for proper functionality
- Gunicorn for production deployment
- Groq for LLM inference
- Pinecone for menu vector search (RAG)

### AI Setup (Optional)

To enable the AI garson (RAG):

1. **Get a Groq API key** from [console.groq.com](https://console.groq.com/)
2. **Get a Pinecone API key** from [app.pinecone.io](https://app.pinecone.io/)
3. **Copy `.env.example` to `.env`** and set `GROQ_API_KEY` and `PINECONE_API_KEY`
4. **Restart the application** — menus are indexed on first chat or via `POST /api/menu/index/<slug>`

**Note**: Without these keys the chatbot is disabled.

### Installation

1. **Clone or navigate to the project directory**
   ```bash
   cd SmartQRMenu
   ```

2. **Create a virtual environment (recommended)**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

### Local Development

1. **Start the Flask server**
   ```bash
   python app.py
   ```

2. **Open your browser and navigate to**
   ```
   http://localhost:5001
   ```

### Deployment on Render.com (önerilen)

Ücretsiz plan; GCP Blaze gerekmez. Detay: **[DEPLOY_RENDER.md](DEPLOY_RENDER.md)**

1. Repo’yu GitHub’a push edin
2. [Render](https://dashboard.render.com/) → **New** → **Blueprint** → repo
3. Ortam değişkenlerini doldurun (`render.env.example`)
4. Firebase → **Authorized domains** → `your-app.onrender.com` ekleyin

**Dosyalar:** `render.yaml`, `Procfile`, `runtime.txt`

### Deployment on Firebase (Hosting + Cloud Run)

GCP faturalandırma gerekir: **[DEPLOY_FIREBASE.md](DEPLOY_FIREBASE.md)**

## API Endpoints

- `GET /` - Main page
- `GET /restaurant` - Restaurant page with AI chatbot (requires authentication)
- `GET /restaurant-info` - Restaurant information page (menu, reviews, details)
- `GET /login` - User login page
- `GET /register` - User registration page
- `GET /profile` - User profile page (requires authentication)
- `GET /logout` - User logout

### API Endpoints
- `GET /api/health` - Health check endpoint
- `POST /api/hello` - Hello endpoint (accepts JSON with "name" field)
- `POST /api/chat` - AI chatbot endpoint (requires authentication, accepts JSON with "question" field)
- `GET /api/ai-status` - AI service status and availability
- `POST /api/auth/verify` - Verify Firebase ID token and create session
- `GET /api/auth/status` - Get current authentication status
- `GET /api/firebase-status` - Firebase service status and availability

### Firestore Database Endpoints
- `GET /api/chat/history` - Get user's chat history (requires authentication)
- `GET /api/user/preferences` - Get user preferences (requires authentication)
- `POST /api/user/preferences` - Update user preferences (requires authentication)
- `GET /api/reviews` - Get restaurant reviews
- `POST /api/reviews` - Post restaurant review (requires authentication)

## Project Structure

```
SmartQRMenu/
├── app.py                 # Main Flask application
├── config.py              # Configuration and environment variables
├── groq_service.py        # Groq LLM integration
├── menu_vector_store.py   # Pinecone menu vector search
├── rag_service.py         # RAG orchestration
├── firebase_config.py     # Firebase authentication service
├── restaurant.json        # Restaurant data (Turkish content)
├── requirements.txt       # Python dependencies
├── render.yaml            # Render.com deployment configuration
├── Procfile               # Alternative deployment configuration
├── README.md              # This file
├── SETUP.md               # Detailed setup instructions
└── templates/             # HTML templates
    ├── landing_base.html  # Base template with Tailwind CSS
    ├── parts/             # Reusable components
    │   ├── navbar.html    # Navigation component with auth
    │   ├── hero.html      # Hero section
    │   └── why_choose_us.html # Features section
    └── pages/             # Page templates
        ├── home.html      # Home page
        ├── restaurant.html # Restaurant page with protected AI chatbot
        ├── restaurant_info.html # Restaurant information page
        ├── login.html     # User login page
        └── register.html  # User registration page
```

## Development

The application runs in debug mode by default, which enables:
- Auto-reload on code changes
- Detailed error messages
- Debug toolbar

## Customization

You can modify the application by:
- Adding new routes in `app.py`
- Updating the UI in `templates/index.html`
- Adding new dependencies to `requirements.txt`

## License

This is a simple demo application. Feel free to modify and use as needed.
