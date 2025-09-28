from flask import request, current_app, g
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import Portfolio, BacktestResult, Transaction, PortfolioHolding
from app.services.backtest_engine import BacktestEngine
from app.tasks.backtest_tasks import run_backtest_async, get_task_status
from app.utils.exceptions import (
    PortfolioNotFoundError, ValidationError, create_error_response, ErrorContext
)
from app.utils.logging_config import get_logger, create_request_logger
from app import db
import traceback

ns = Namespace('backtests', description='回测相关接口')

# API 模型定义
backtest_model = ns.model('BacktestResult', {
    'id': fields.Integer(description='回测ID'),
    'portfolio_id': fields.Integer(description='组合ID'),
    'name': fields.String(description='回测名称'),
    'start_date': fields.String(description='开始日期'),
    'end_date': fields.String(description='结束日期'),
    'initial_capital': fields.Float(description='初始资金'),
    'final_value': fields.Float(description='最终价值'),
    'total_return': fields.Float(description='总收益率'),
    'annualized_return': fields.Float(description='年化收益率'),
    'max_drawdown': fields.Float(description='最大回撤'),
    'sharpe_ratio': fields.Float(description='夏普比率'),
    'volatility': fields.Float(description='波动率'),
    'total_trades': fields.Integer(description='交易次数'),
    'total_fees': fields.Float(description='总手续费'),
    'created_at': fields.String(description='创建时间')
})

backtest_create_model = ns.model('BacktestCreate', {
    'portfolio_id': fields.Integer(required=True, description='组合ID'),
    'name': fields.String(description='回测名称'),
    'start_date': fields.String(required=True, description='开始日期'),
    'end_date': fields.String(required=True, description='结束日期'),
    'async_mode': fields.Boolean(default=True, description='是否异步执行')
})

task_status_model = ns.model('TaskStatus', {
    'task_id': fields.String(description='任务ID'),
    'state': fields.String(description='任务状态'),
    'current': fields.Integer(description='当前进度'),
    'total': fields.Integer(description='总进度'),
    'status': fields.String(description='状态描述'),
    'result': fields.Raw(description='任务结果'),
    'error': fields.String(description='错误信息')
})

async_backtest_response_model = ns.model('AsyncBacktestResponse', {
    'task_id': fields.String(description='任务ID'),
    'message': fields.String(description='消息'),
    'status_url': fields.String(description='状态查询URL')
})

transaction_model = ns.model('Transaction', {
    'id': fields.Integer(description='交易ID'),
    'portfolio_id': fields.Integer(description='组合ID'),
    'instrument_id': fields.Integer(description='标的ID'),
    'instrument': fields.Raw(description='标的信息'),
    'backtest_result_id': fields.Integer(description='回测ID'),
    'transaction_date': fields.String(description='交易日期'),
    'transaction_type': fields.String(description='交易类型'),
    'quantity': fields.Float(description='数量'),
    'price': fields.Float(description='价格'),
    'fee': fields.Float(description='手续费'),
    'total_amount': fields.Float(description='总金额'),
    'exchange_rate': fields.Float(description='汇率'),
    'notes': fields.String(description='备注'),
    'created_at': fields.String(description='创建时间')
})

holding_model = ns.model('PortfolioHolding', {
    'id': fields.Integer(description='持仓ID'),
    'portfolio_id': fields.Integer(description='组合ID'),
    'instrument_id': fields.Integer(description='标的ID'),
    'instrument': fields.Raw(description='标的信息'),
    'backtest_result_id': fields.Integer(description='回测ID'),
    'holding_date': fields.String(description='持仓日期'),
    'quantity': fields.Float(description='持仓数量'),
    'average_cost': fields.Float(description='平均成本'),
    'market_value': fields.Float(description='市值'),
    'unrealized_pnl': fields.Float(description='未实现盈亏'),
    'weight': fields.Float(description='权重'),
    'created_at': fields.String(description='创建时间')
})

@ns.route('')
class BacktestList(Resource):
    @ns.marshal_list_with(backtest_model)
    @jwt_required()
    def get(self):
        """获取用户回测结果列表"""
        user_id = int(get_jwt_identity())
        portfolio_id = request.args.get('portfolio_id', type=int)

        query = db.session.query(BacktestResult).join(Portfolio).filter(Portfolio.user_id == user_id)

        if portfolio_id:
            query = query.filter(BacktestResult.portfolio_id == portfolio_id)

        backtests = query.order_by(BacktestResult.created_at.desc()).all()

        return [backtest.to_dict() for backtest in backtests]

@ns.route('/tasks/<string:task_id>/status')
class TaskStatus(Resource):
    @ns.marshal_with(task_status_model)
    @jwt_required()
    def get(self, task_id):
        """查询异步任务状态"""
        logger = create_request_logger(g.get('request_id'))
        user_id = int(get_jwt_identity())

        logger.info(f"用户 {user_id} 查询任务状态: {task_id}")

        try:
            from celery.result import AsyncResult
            from app.tasks import celery

            # 获取任务结果
            task_result = AsyncResult(task_id, app=celery)

            if task_result.state == 'PENDING':
                response = {
                    'task_id': task_id,
                    'state': task_result.state,
                    'current': 0,
                    'total': 100,
                    'status': '等待处理...'
                }
            elif task_result.state == 'PROGRESS':
                response = {
                    'task_id': task_id,
                    'state': task_result.state,
                    'current': task_result.info.get('current', 0),
                    'total': task_result.info.get('total', 100),
                    'status': task_result.info.get('status', '处理中...')
                }
            elif task_result.state == 'SUCCESS':
                response = {
                    'task_id': task_id,
                    'state': task_result.state,
                    'current': 100,
                    'total': 100,
                    'status': '任务完成',
                    'result': task_result.result
                }
            else:  # FAILURE
                response = {
                    'task_id': task_id,
                    'state': task_result.state,
                    'current': 0,
                    'total': 100,
                    'status': '任务失败',
                    'error': str(task_result.info) if task_result.info else '未知错误'
                }

            return response

        except Exception as e:
            logger.error(f"查询任务状态失败: {str(e)}", exc_info=True)
            return {
                'task_id': task_id,
                'state': 'FAILURE',
                'current': 0,
                'total': 100,
                'status': '查询失败',
                'error': str(e)
            }, 500

@ns.route('/tasks/<string:task_id>/cancel')
class TaskCancel(Resource):
    @jwt_required()
    def post(self, task_id):
        """取消异步任务"""
        logger = create_request_logger(g.get('request_id'))
        user_id = int(get_jwt_identity())

        logger.info(f"用户 {user_id} 请求取消任务: {task_id}")

        try:
            from celery.result import AsyncResult
            from app.tasks import celery

            # 撤销任务
            celery.control.revoke(task_id, terminate=True)

            logger.info(f"任务 {task_id} 已被取消")

            return {
                'message': f'任务 {task_id} 已取消',
                'task_id': task_id,
                'status': 'cancelled'
            }, 200

        except Exception as e:
            logger.error(f"取消任务失败: {str(e)}", exc_info=True)
            return {
                'message': f'取消任务失败: {str(e)}',
                'task_id': task_id
            }, 500

    @ns.expect(backtest_create_model)
    @jwt_required()
    def post(self):
        """发起回测（支持异步模式）"""
        logger = create_request_logger(g.get('request_id'))
        user_id = int(get_jwt_identity())
        data = request.get_json()

        with ErrorContext("回测创建", user_id=user_id, portfolio_id=data.get('portfolio_id')):
            # 数据验证
            if not data.get('portfolio_id'):
                raise ValidationError("portfolio_id 是必需的", field='portfolio_id')

            if not data.get('start_date'):
                raise ValidationError("start_date 是必需的", field='start_date')

            if not data.get('end_date'):
                raise ValidationError("end_date 是必需的", field='end_date')

            # 验证日期格式
            try:
                from datetime import datetime
                start_dt = datetime.strptime(data['start_date'], '%Y-%m-%d')
                end_dt = datetime.strptime(data['end_date'], '%Y-%m-%d')

                if start_dt >= end_dt:
                    raise ValidationError("结束日期必须晚于开始日期")

            except ValueError as e:
                raise ValidationError(f"日期格式错误: {str(e)}")

            # 验证投资组合是否属于当前用户
            portfolio = Portfolio.query.filter_by(
                id=data['portfolio_id'],
                user_id=user_id
            ).first()

            if not portfolio:
                raise PortfolioNotFoundError(data['portfolio_id'])

            logger.info(f"用户 {user_id} 发起投资组合 {data['portfolio_id']} 的回测")

            # 判断是否使用异步模式
            async_mode = data.get('async_mode', True)

            if async_mode:
                # 异步模式：启动Celery任务
                task = run_backtest_async.delay(
                    portfolio_id=data['portfolio_id'],
                    start_date=data['start_date'],
                    end_date=data['end_date'],
                    name=data.get('name')
                )

                logger.info(f"异步回测任务已启动: {task.id}")

                response_data = {
                    'task_id': task.id,
                    'message': '回测任务已启动，请查询任务状态获取进度',
                    'status_url': f'/api/backtests/tasks/{task.id}/status',
                    'async_mode': True
                }

                return response_data, 202

            else:
                # 同步模式：直接执行
                logger.info("使用同步模式执行回测")

                engine = BacktestEngine()
                result = engine.run_backtest(
                    portfolio_id=data['portfolio_id'],
                    start_date=data['start_date'],
                    end_date=data['end_date'],
                    name=data.get('name')
                )

                logger.info(f"同步回测完成: 回测ID {result.id}")
                return result.to_dict(), 201

@ns.route('/<int:backtest_id>')
class BacktestDetail(Resource):
    @ns.marshal_with(backtest_model)
    @jwt_required()
    def get(self, backtest_id):
        """获取回测结果详情"""
        user_id = int(get_jwt_identity())

        backtest = db.session.query(BacktestResult).join(Portfolio).filter(
            BacktestResult.id == backtest_id,
            Portfolio.user_id == user_id
        ).first()

        if not backtest:
            return {'message': '回测结果不存在'}, 404

        return backtest.to_dict()

    @jwt_required()
    def delete(self, backtest_id):
        """删除回测结果"""
        user_id = int(get_jwt_identity())

        backtest = db.session.query(BacktestResult).join(Portfolio).filter(
            BacktestResult.id == backtest_id,
            Portfolio.user_id == user_id
        ).first()

        if not backtest:
            return {'message': '回测结果不存在'}, 404

        db.session.delete(backtest)
        db.session.commit()

        return {'message': '回测结果已删除'}, 200

@ns.route('/<int:backtest_id>/transactions')
class BacktestTransactions(Resource):
    @ns.marshal_list_with(transaction_model)
    @jwt_required()
    def get(self, backtest_id):
        """获取回测交易记录"""
        user_id = int(get_jwt_identity())

        # 验证回测结果是否属于当前用户
        backtest = db.session.query(BacktestResult).join(Portfolio).filter(
            BacktestResult.id == backtest_id,
            Portfolio.user_id == user_id
        ).first()

        if not backtest:
            return {'message': '回测结果不存在'}, 404

        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)

        transactions = Transaction.query.filter_by(
            backtest_result_id=backtest_id
        ).order_by(Transaction.transaction_date.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return [trans.to_dict() for trans in transactions.items]

@ns.route('/<int:backtest_id>/holdings')
class BacktestHoldings(Resource):
    @ns.marshal_list_with(holding_model)
    @jwt_required()
    def get(self, backtest_id):
        """获取回测持仓记录"""
        user_id = int(get_jwt_identity())

        # 验证回测结果是否属于当前用户
        backtest = db.session.query(BacktestResult).join(Portfolio).filter(
            BacktestResult.id == backtest_id,
            Portfolio.user_id == user_id
        ).first()

        if not backtest:
            return {'message': '回测结果不存在'}, 404

        date = request.args.get('date')  # 获取指定日期的持仓
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)

        query = PortfolioHolding.query.filter_by(backtest_result_id=backtest_id)

        if date:
            from datetime import datetime
            try:
                holding_date = datetime.strptime(date, '%Y-%m-%d').date()
                query = query.filter_by(holding_date=holding_date)
            except ValueError:
                return {'message': '日期格式错误，请使用YYYY-MM-DD格式'}, 400

        holdings = query.order_by(PortfolioHolding.holding_date.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return [holding.to_dict() for holding in holdings.items]

@ns.route('/<int:backtest_id>/performance')
class BacktestPerformance(Resource):
    @jwt_required()
    def get(self, backtest_id):
        """获取回测绩效数据"""
        user_id = int(get_jwt_identity())

        # 验证回测结果是否属于当前用户
        backtest = db.session.query(BacktestResult).join(Portfolio).filter(
            BacktestResult.id == backtest_id,
            Portfolio.user_id == user_id
        ).first()

        if not backtest:
            return {'message': '回测结果不存在'}, 404

        performance_data = {
            'basic_metrics': {
                'initial_capital': float(backtest.initial_capital),
                'final_value': float(backtest.final_value),
                'total_return': float(backtest.total_return),
                'annualized_return': float(backtest.annualized_return),
                'max_drawdown': float(backtest.max_drawdown) if backtest.max_drawdown else None,
                'sharpe_ratio': float(backtest.sharpe_ratio) if backtest.sharpe_ratio else None,
                'volatility': float(backtest.volatility) if backtest.volatility else None,
                'total_trades': backtest.total_trades,
                'total_fees': float(backtest.total_fees)
            },
            'daily_values': backtest.result_data.get('daily_values', []) if backtest.result_data else [],
            'detailed_metrics': backtest.result_data.get('metrics', {}) if backtest.result_data else {}
        }

        return performance_data

@ns.route('/portfolio/<int:portfolio_id>')
class PortfolioBacktests(Resource):
    @ns.marshal_list_with(backtest_model)
    @jwt_required()
    def get(self, portfolio_id):
        """获取指定投资组合的所有回测结果"""
        user_id = int(get_jwt_identity())

        # 验证投资组合是否属于当前用户
        portfolio = Portfolio.query.filter_by(
            id=portfolio_id,
            user_id=user_id
        ).first()

        if not portfolio:
            return {'message': '投资组合不存在'}, 404

        backtests = BacktestResult.query.filter_by(
            portfolio_id=portfolio_id
        ).order_by(BacktestResult.created_at.desc()).all()

        return [backtest.to_dict() for backtest in backtests]