from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from config import config

db = SQLAlchemy()
jwt = JWTManager()

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)
    CORS(app)

    # Register blueprints
    from app.api import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

    # Add main routes
    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/health')
    def health_check():
        return {'status': 'healthy', 'message': 'Portfolio Backtest API is running'}

    # Create database tables
    with app.app_context():
        db.create_all()

    return app