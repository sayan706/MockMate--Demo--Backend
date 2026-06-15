import os
from flask import Flask
from flask_socketio import SocketIO
from flask_cors import CORS

# Initialize extensions globally
socketio = SocketIO(cors_allowed_origins="*")
cors = CORS()

# Global dictionary to store active interview sessions
sessions = {}

def create_app():
    app = Flask(__name__)
    
    # Load configuration
    from app.config import Config
    app.config.from_object(Config)

    # Ensure upload folder exists
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    app.config['UPLOAD_FOLDER'] = Config.UPLOAD_FOLDER
    app.config['MAX_CONTENT_LENGTH'] = Config.MAX_CV_SIZE_MB * 1024 * 1024  # MB to bytes

    # Initialize extensions with app context
    cors.init_app(app)
    socketio.init_app(app)

    # Register Blueprints (Routes)
    from app.routes.api import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

    from app.routes.tts import tts_bp
    app.register_blueprint(tts_bp, url_prefix='/api')

    # Register Socket events
    # We just need to import them so the decorators are executed
    from app.sockets import events

    return app
