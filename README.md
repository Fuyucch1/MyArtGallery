# Art Gallery Application

A Flask-based web application for managing and displaying art commissions and references.

## Installation

1. Clone the repository
2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Running the Application

### Development Mode

To run the application in development mode:

```
python app.py
```

This will start the Flask development server on port 8000.

### Production Mode with Gunicorn

To run the application in production mode with Gunicorn:

```
gunicorn -c gunicorn_config.py app:app
```

Or simply use the provided batch script (Windows):

```
start_server.bat
```

This will start Gunicorn on port 8000 with the configuration specified in `gunicorn_config.py`.

## Configuration

The application can be configured through the following files:

- `app.py` - Main application file
- `gunicorn_config.py` - Gunicorn configuration for production deployment
- `start_server.bat` - Windows batch script to start the application with Gunicorn

## Features

- Art commission management
- Reference image organization
- User authentication
- Custom reference links
