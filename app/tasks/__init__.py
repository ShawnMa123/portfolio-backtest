from celery import Celery
from config import config
import os

def make_celery(app=None):
    """创建Celery实例"""
    config_name = os.environ.get('FLASK_ENV', 'default')
    current_config = config[config_name]

    celery = Celery(
        app.import_name if app else 'portfolio-backtest',
        broker=current_config.CELERY_BROKER_URL,
        backend=current_config.CELERY_RESULT_BACKEND,
        include=['app.tasks.backtest_tasks']
    )

    # 配置任务
    celery.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
        task_track_started=True,
        result_expires=3600,
        worker_prefetch_multiplier=1,
        task_routes={
            'app.tasks.backtest_tasks.run_backtest_async': {'queue': 'backtest'},
            'app.tasks.backtest_tasks.sync_instrument_data_async': {'queue': 'data_sync'},
        }
    )

    if app:
        # 更新任务基类以支持Flask应用上下文
        class ContextTask(celery.Task):
            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return self.run(*args, **kwargs)

        celery.Task = ContextTask

    return celery

# 创建默认Celery实例
celery = make_celery()