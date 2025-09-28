"""
结构化日志配置
"""
import logging
import logging.config
import json
import os
from datetime import datetime
from typing import Dict, Any

class StructuredFormatter(logging.Formatter):
    """结构化日志格式化器"""

    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录为JSON格式"""

        # 基础日志数据
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }

        # 添加额外的上下文信息
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id

        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id

        if hasattr(record, 'task_id'):
            log_data['task_id'] = record.task_id

        # 添加异常信息
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': self.formatException(record.exc_info)
            }

        # 添加自定义字段
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                          'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
                          'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                          'thread', 'threadName', 'processName', 'process', 'message']:
                if not key.startswith('_'):
                    log_data[key] = value

        return json.dumps(log_data, ensure_ascii=False, default=str)

class RequestContextFilter(logging.Filter):
    """请求上下文过滤器，添加请求相关信息"""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            from flask import has_request_context, request, g

            if has_request_context():
                record.request_method = request.method
                record.request_path = request.path
                record.request_remote_addr = request.remote_addr

                # 添加用户ID（如果已登录）
                if hasattr(g, 'current_user_id'):
                    record.user_id = g.current_user_id

                # 添加请求ID（如果存在）
                if hasattr(g, 'request_id'):
                    record.request_id = g.request_id

        except RuntimeError:
            # 在应用上下文之外运行
            pass

        return True

def setup_logging(app=None) -> None:
    """
    设置应用日志配置

    Args:
        app: Flask应用实例
    """

    # 创建日志目录
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 日志配置
    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'structured': {
                '()': StructuredFormatter,
            },
            'simple': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            }
        },
        'filters': {
            'request_context': {
                '()': RequestContextFilter,
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': 'INFO',
                'formatter': 'simple',
                'filters': ['request_context'],
                'stream': 'ext://sys.stdout'
            },
            'file_structured': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'INFO',
                'formatter': 'structured',
                'filters': ['request_context'],
                'filename': os.path.join(log_dir, 'app.jsonl'),
                'maxBytes': 10485760,  # 10MB
                'backupCount': 10,
                'encoding': 'utf-8'
            },
            'error_file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'ERROR',
                'formatter': 'structured',
                'filters': ['request_context'],
                'filename': os.path.join(log_dir, 'error.jsonl'),
                'maxBytes': 10485760,  # 10MB
                'backupCount': 10,
                'encoding': 'utf-8'
            },
            'celery_file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'INFO',
                'formatter': 'structured',
                'filename': os.path.join(log_dir, 'celery.jsonl'),
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5,
                'encoding': 'utf-8'
            }
        },
        'loggers': {
            'app': {
                'level': 'INFO',
                'handlers': ['console', 'file_structured', 'error_file'],
                'propagate': False
            },
            'app.tasks': {
                'level': 'INFO',
                'handlers': ['console', 'celery_file', 'error_file'],
                'propagate': False
            },
            'app.services': {
                'level': 'INFO',
                'handlers': ['console', 'file_structured', 'error_file'],
                'propagate': False
            },
            'celery': {
                'level': 'INFO',
                'handlers': ['console', 'celery_file'],
                'propagate': False
            },
            'werkzeug': {
                'level': 'WARNING',
                'handlers': ['console'],
                'propagate': False
            }
        },
        'root': {
            'level': 'INFO',
            'handlers': ['console', 'file_structured']
        }
    }

    # 在调试模式下降低日志级别
    if app and app.debug:
        logging_config['handlers']['console']['level'] = 'DEBUG'
        logging_config['loggers']['app']['level'] = 'DEBUG'
        logging_config['loggers']['app.tasks']['level'] = 'DEBUG'
        logging_config['loggers']['app.services']['level'] = 'DEBUG'

    # 应用日志配置
    logging.config.dictConfig(logging_config)

    if app:
        app.logger.info("结构化日志系统初始化完成")

def get_logger(name: str) -> logging.Logger:
    """
    获取配置好的日志器

    Args:
        name: 日志器名称

    Returns:
        logging.Logger: 配置好的日志器
    """
    return logging.getLogger(name)

class LoggerAdapter(logging.LoggerAdapter):
    """
    日志适配器，用于添加上下文信息
    """

    def __init__(self, logger: logging.Logger, extra: Dict[str, Any] = None):
        super().__init__(logger, extra or {})

    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        """处理日志消息，添加额外信息"""
        # 合并额外信息
        if 'extra' in kwargs:
            kwargs['extra'].update(self.extra)
        else:
            kwargs['extra'] = self.extra.copy()

        return msg, kwargs

def create_task_logger(task_id: str) -> LoggerAdapter:
    """
    创建任务专用日志器

    Args:
        task_id: 任务ID

    Returns:
        LoggerAdapter: 带任务ID的日志器
    """
    logger = get_logger('app.tasks')
    return LoggerAdapter(logger, {'task_id': task_id})

def create_request_logger(request_id: str = None) -> LoggerAdapter:
    """
    创建请求专用日志器

    Args:
        request_id: 请求ID

    Returns:
        LoggerAdapter: 带请求ID的日志器
    """
    import uuid
    logger = get_logger('app')
    return LoggerAdapter(logger, {'request_id': request_id or str(uuid.uuid4())})

# 性能监控日志装饰器
def log_performance(operation: str = None):
    """
    性能监控装饰器

    Args:
        operation: 操作名称

    Returns:
        装饰器函数
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            import time
            import functools

            logger = get_logger('app.performance')
            op_name = operation or f"{func.__module__}.{func.__name__}"

            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                logger.info(
                    f"操作完成: {op_name}",
                    extra={
                        'operation': op_name,
                        'duration': duration,
                        'status': 'success'
                    }
                )
                return result

            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    f"操作失败: {op_name} - {str(e)}",
                    extra={
                        'operation': op_name,
                        'duration': duration,
                        'status': 'error',
                        'exception_type': type(e).__name__
                    },
                    exc_info=True
                )
                raise

        return functools.wraps(func)(wrapper)
    return decorator