from celery import current_task
from app.tasks import celery
from app.services.backtest_engine import BacktestEngine
from app.services.data_service import DataService
from app.models import Portfolio, BacktestResult
from app import db
from datetime import datetime
import traceback
import logging

logger = logging.getLogger(__name__)

@celery.task(bind=True, name='app.tasks.backtest_tasks.run_backtest_async')
def run_backtest_async(self, portfolio_id: int, start_date: str, end_date: str, name: str = None):
    """
    异步执行投资组合回测

    Args:
        portfolio_id: 投资组合ID
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
        name: 回测名称

    Returns:
        dict: 回测结果
    """
    task_id = self.request.id

    try:
        # 更新任务状态：开始处理
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 0,
                'total': 100,
                'status': '初始化回测引擎...',
                'task_id': task_id
            }
        )

        # 验证投资组合存在
        portfolio = Portfolio.query.get(portfolio_id)
        if not portfolio:
            raise ValueError(f"投资组合 {portfolio_id} 不存在")

        logger.info(f"开始异步回测任务 {task_id}: 投资组合 {portfolio_id}")

        # 初始化回测引擎
        engine = BacktestEngine()

        # 更新进度：准备数据
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 20,
                'total': 100,
                'status': '准备价格数据...',
                'task_id': task_id
            }
        )

        # 执行回测
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 40,
                'total': 100,
                'status': '执行回测计算...',
                'task_id': task_id
            }
        )

        # 调用原有回测逻辑
        backtest_result = engine.run_backtest(
            portfolio_id=portfolio_id,
            start_date=start_date,
            end_date=end_date,
            name=name or f"异步回测 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )

        # 更新进度：计算完成
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 80,
                'total': 100,
                'status': '保存回测结果...',
                'task_id': task_id
            }
        )

        # 准备返回结果
        result_data = {
            'task_id': task_id,
            'backtest_result_id': backtest_result.id,
            'portfolio_id': portfolio_id,
            'total_return': float(backtest_result.total_return or 0),
            'annualized_return': float(backtest_result.annualized_return or 0),
            'final_value': float(backtest_result.final_value or 0),
            'max_drawdown': float(backtest_result.max_drawdown or 0),
            'sharpe_ratio': float(backtest_result.sharpe_ratio or 0),
            'volatility': float(backtest_result.volatility or 0),
            'total_trades': backtest_result.total_trades or 0,
            'total_fees': float(backtest_result.total_fees or 0),
            'start_date': start_date,
            'end_date': end_date,
            'status': 'completed',
            'completed_at': datetime.now().isoformat()
        }

        logger.info(f"异步回测任务 {task_id} 完成成功")

        return result_data

    except Exception as exc:
        logger.error(f"异步回测任务 {task_id} 失败: {str(exc)}")
        logger.error(f"错误详情: {traceback.format_exc()}")

        # 更新任务失败状态
        self.update_state(
            state='FAILURE',
            meta={
                'error': str(exc),
                'traceback': traceback.format_exc(),
                'task_id': task_id,
                'status': 'failed'
            }
        )

        # 重新抛出异常
        raise exc

@celery.task(bind=True, name='app.tasks.backtest_tasks.sync_instrument_data_async')
def sync_instrument_data_async(self, symbol: str, days: int = 365):
    """
    异步同步金融工具数据

    Args:
        symbol: 金融工具代码
        days: 同步天数

    Returns:
        dict: 同步结果
    """
    task_id = self.request.id

    try:
        logger.info(f"开始异步数据同步任务 {task_id}: {symbol}")

        self.update_state(
            state='PROGRESS',
            meta={
                'current': 0,
                'total': 100,
                'status': f'开始同步 {symbol} 数据...',
                'task_id': task_id
            }
        )

        # 初始化数据服务
        data_service = DataService()

        self.update_state(
            state='PROGRESS',
            meta={
                'current': 50,
                'total': 100,
                'status': f'从外部API获取 {symbol} 数据...',
                'task_id': task_id
            }
        )

        # 执行数据同步
        success = data_service.sync_instrument_data(symbol, days)

        if success:
            result_data = {
                'task_id': task_id,
                'symbol': symbol,
                'days': days,
                'status': 'completed',
                'message': f'{symbol} 数据同步成功',
                'completed_at': datetime.now().isoformat()
            }
            logger.info(f"异步数据同步任务 {task_id} 完成成功")
        else:
            raise Exception(f"数据同步失败: {symbol}")

        return result_data

    except Exception as exc:
        logger.error(f"异步数据同步任务 {task_id} 失败: {str(exc)}")

        self.update_state(
            state='FAILURE',
            meta={
                'error': str(exc),
                'task_id': task_id,
                'status': 'failed'
            }
        )

        raise exc

@celery.task(bind=True, name='app.tasks.backtest_tasks.get_task_status')
def get_task_status(task_id: str):
    """
    获取任务状态

    Args:
        task_id: 任务ID

    Returns:
        dict: 任务状态信息
    """
    try:
        task_result = celery.AsyncResult(task_id)

        if task_result.state == 'PENDING':
            response = {
                'state': task_result.state,
                'current': 0,
                'total': 1,
                'status': '等待处理...'
            }
        elif task_result.state != 'FAILURE':
            response = {
                'state': task_result.state,
                'current': task_result.info.get('current', 0),
                'total': task_result.info.get('total', 1),
                'status': task_result.info.get('status', '')
            }
            if 'result' in task_result.info:
                response['result'] = task_result.info['result']
        else:
            response = {
                'state': task_result.state,
                'current': 1,
                'total': 1,
                'status': '任务失败',
                'error': str(task_result.info)
            }

        return response

    except Exception as exc:
        return {
            'state': 'FAILURE',
            'error': str(exc),
            'status': '获取任务状态失败'
        }