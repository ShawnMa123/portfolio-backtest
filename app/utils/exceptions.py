"""
自定义异常类和错误处理工具
"""
import logging
from typing import Dict, Any, Optional
from flask import jsonify, request
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)

class BacktestException(Exception):
    """回测相关异常基类"""

    def __init__(self, message: str, error_code: str = None, details: Dict = None):
        self.message = message
        self.error_code = error_code or 'BACKTEST_ERROR'
        self.details = details or {}
        super().__init__(self.message)

class ValidationError(BacktestException):
    """数据验证异常"""

    def __init__(self, message: str, field: str = None, details: Dict = None):
        self.field = field
        super().__init__(message, 'VALIDATION_ERROR', details)

class DataServiceError(BacktestException):
    """数据服务异常"""

    def __init__(self, message: str, symbol: str = None, details: Dict = None):
        self.symbol = symbol
        super().__init__(message, 'DATA_SERVICE_ERROR', details)

class PortfolioNotFoundError(BacktestException):
    """投资组合未找到异常"""

    def __init__(self, portfolio_id: int):
        message = f"投资组合 {portfolio_id} 未找到"
        super().__init__(message, 'PORTFOLIO_NOT_FOUND', {'portfolio_id': portfolio_id})

class InstrumentNotFoundError(BacktestException):
    """金融工具未找到异常"""

    def __init__(self, symbol: str):
        message = f"金融工具 {symbol} 未找到"
        super().__init__(message, 'INSTRUMENT_NOT_FOUND', {'symbol': symbol})

class InsufficientDataError(BacktestException):
    """数据不足异常"""

    def __init__(self, symbol: str, start_date: str, end_date: str):
        message = f"金融工具 {symbol} 在 {start_date} 到 {end_date} 期间数据不足"
        super().__init__(
            message,
            'INSUFFICIENT_DATA',
            {'symbol': symbol, 'start_date': start_date, 'end_date': end_date}
        )

class TaskError(BacktestException):
    """异步任务异常"""

    def __init__(self, task_id: str, message: str, details: Dict = None):
        self.task_id = task_id
        super().__init__(message, 'TASK_ERROR', details)

def create_error_response(
    error: Exception,
    status_code: int = 500,
    include_traceback: bool = False
) -> tuple:
    """
    创建标准化的错误响应

    Args:
        error: 异常对象
        status_code: HTTP状态码
        include_traceback: 是否包含堆栈跟踪

    Returns:
        tuple: (response, status_code)
    """
    import traceback

    if isinstance(error, BacktestException):
        error_data = {
            'error': {
                'code': error.error_code,
                'message': error.message,
                'details': error.details,
                'timestamp': logger.getEffectiveLevel() <= logging.DEBUG and
                           __import__('datetime').datetime.now().isoformat()
            }
        }

        # 根据异常类型设置状态码
        if isinstance(error, ValidationError):
            status_code = 400
        elif isinstance(error, (PortfolioNotFoundError, InstrumentNotFoundError)):
            status_code = 404
        elif isinstance(error, DataServiceError):
            status_code = 503

    elif isinstance(error, HTTPException):
        error_data = {
            'error': {
                'code': 'HTTP_ERROR',
                'message': error.description,
                'details': {'status_code': error.code}
            }
        }
        status_code = error.code

    else:
        # 未预期的异常
        error_data = {
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'Internal server error',
                'details': {}
            }
        }

        # 在调试模式下包含详细错误信息
        if include_traceback or logger.getEffectiveLevel() <= logging.DEBUG:
            error_data['error']['details'] = {
                'exception_type': type(error).__name__,
                'exception_message': str(error)
            }

            if include_traceback:
                error_data['error']['traceback'] = traceback.format_exc()

    # 记录错误日志
    logger.error(
        f"API错误: {error_data['error']['message']}",
        extra={
            'error_code': error_data['error']['code'],
            'request_path': request.path if request else None,
            'request_method': request.method if request else None,
            'status_code': status_code,
            'exception_type': type(error).__name__
        },
        exc_info=True
    )

    return jsonify(error_data), status_code

def register_error_handlers(app):
    """
    注册全局错误处理器

    Args:
        app: Flask应用实例
    """

    @app.errorhandler(BacktestException)
    def handle_backtest_exception(error):
        return create_error_response(error)

    @app.errorhandler(ValidationError)
    def handle_validation_error(error):
        return create_error_response(error, 400)

    @app.errorhandler(404)
    def handle_not_found(error):
        return create_error_response(error, 404)

    @app.errorhandler(500)
    def handle_internal_error(error):
        return create_error_response(error, 500)

    @app.errorhandler(Exception)
    def handle_generic_exception(error):
        # 对于未处理的异常，返回通用错误响应
        return create_error_response(error, 500, include_traceback=app.debug)

    logger.info("全局错误处理器注册完成")

class ErrorContext:
    """错误上下文管理器，用于收集和记录错误信息"""

    def __init__(self, operation: str, **context):
        self.operation = operation
        self.context = context
        self.start_time = None

    def __enter__(self):
        import time
        self.start_time = time.time()
        logger.debug(f"开始操作: {self.operation}", extra=self.context)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        import time
        duration = time.time() - self.start_time if self.start_time else 0

        if exc_type is None:
            logger.debug(
                f"操作完成: {self.operation} (耗时: {duration:.2f}s)",
                extra={**self.context, 'duration': duration}
            )
        else:
            logger.error(
                f"操作失败: {self.operation} (耗时: {duration:.2f}s) - {exc_val}",
                extra={
                    **self.context,
                    'duration': duration,
                    'exception_type': exc_type.__name__,
                    'exception_message': str(exc_val)
                },
                exc_info=True
            )

        # 不抑制异常
        return False