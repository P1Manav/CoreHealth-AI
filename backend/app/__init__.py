# Flask application factory.
from flask import Flask
from flask_cors import CORS


def create_app():
    app = Flask(__name__)
    CORS(app, resources={
        r"/api/*": {
            "origins": ["http://localhost:5173", "http://127.0.0.1:5173"],
            "allow_headers": ["Content-Type", "Authorization", "X-Guest-Session-Id"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        }
    })
    from app.routes import api_bp
    app.register_blueprint(api_bp, url_prefix="/api")
    return app
