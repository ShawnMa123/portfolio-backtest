#!/usr/bin/env python3
"""
Celery Worker 启动脚本
"""
import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.tasks import make_celery

# 创建Flask应用
app = create_app(os.environ.get('FLASK_ENV', 'default'))

# 创建Celery实例
celery = make_celery(app)

if __name__ == '__main__':
    # 启动worker
    celery.start(['worker', '--loglevel=info', '--concurrency=2'])