from flask import Flask, render_template, g
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from config import config
import sys
import os
import uuid

# 设置UTF-8编码
if sys.platform.startswith('win'):
    os.environ['PYTHONIOENCODING'] = 'utf-8'

db = SQLAlchemy()
jwt = JWTManager()

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # 设置默认字符编码
    app.config['JSON_AS_ASCII'] = False

    # 初始化日志系统
    from app.utils.logging_config import setup_logging
    setup_logging(app)

    # 注册错误处理器
    from app.utils.exceptions import register_error_handlers
    register_error_handlers(app)

    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)
    CORS(app)

    # 初始化Celery
    from app.tasks import make_celery
    celery = make_celery(app)
    app.celery = celery

    # 请求前处理 - 添加请求ID
    @app.before_request
    def before_request():
        g.request_id = str(uuid.uuid4())
        app.logger.debug(f"请求开始: {g.request_id}")

    # 请求后处理
    @app.after_request
    def after_request(response):
        if hasattr(g, 'request_id'):
            response.headers['X-Request-ID'] = g.request_id
            app.logger.debug(f"请求完成: {g.request_id} - 状态码: {response.status_code}")
        return response

    # Register blueprints
    from app.api import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

    # Add main routes
    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/backtest')
    def backtest_tool():
        return render_template('backtest.html')

    @app.route('/demo')
    def demo():
        return render_template('demo.html')

    @app.route('/health')
    def health_check():
        return {
            'status': 'healthy',
            'message': 'Portfolio Backtest API is running',
            'request_id': g.get('request_id'),
            'celery_status': 'active' if hasattr(app, 'celery') else 'inactive'
        }

    # Create database tables
    with app.app_context():
        db.create_all()
        app.logger.info("数据库表创建完成")

    return app