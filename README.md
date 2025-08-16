# SmartQRMenu - Flask Application

A simple Flask web application with a modern, responsive UI.

## Features

- Clean, modern web interface
- Health check API endpoint
- Hello API endpoint with POST support
- Responsive design with gradient background
- Interactive JavaScript functionality

## Setup

### Prerequisites
- Python 3.7 or higher
- pip (Python package installer)

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
   - **Environment:** Python 3.9
5. **Deploy!**

The `render.yaml` file is included for easy deployment configuration.

## API Endpoints

- `GET /` - Main page
- `GET /api/health` - Health check endpoint
- `POST /api/hello` - Hello endpoint (accepts JSON with "name" field)

## Project Structure

```
SmartQRMenu/
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── README.md          # This file
└── templates/         # HTML templates
    └── index.html     # Main page template
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
