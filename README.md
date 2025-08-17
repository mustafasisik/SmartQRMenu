# SmartQRMenu - Flask Application

A simple Flask web application with a modern, responsive UI.

## Features

- Clean, modern web interface
- Restaurant information page with comprehensive details
- Restaurant page with **Gemini AI chatbot** powered by Google AI
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
- Google Generative AI for Gemini AI integration

### AI Setup (Optional)

To enable the Gemini AI chatbot:

1. **Get a Gemini API key** from [Google AI Studio](https://makersuite.google.com/app/apikey)
2. **Create a `.env` file** in the project root:
   ```bash
   GEMINI_API_KEY=your_actual_api_key_here
   ```
3. **Restart the application** - the AI service will automatically initialize

**Note**: The application works without the AI key, but the chatbot will be disabled.

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

### Deployment on Render.com

1. **Push your code to GitHub/GitLab**
2. **Connect your repository to Render**
3. **Create a new Web Service**
4. **Use the following settings:**
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
   - **Environment:** Python 3.11
5. **Deploy!**

**Deployment Files Included:**
- `render.yaml` - Automatic deployment configuration
- `Procfile` - Alternative deployment method
- `requirements.txt` - Compatible dependency versions

## API Endpoints

- `GET /` - Main page
- `GET /restaurant` - Restaurant page with Gemini AI chatbot (requires authentication)
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
├── gemini_service.py      # Gemini AI service integration
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
