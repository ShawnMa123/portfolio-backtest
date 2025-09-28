from flask import request
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import Portfolio, BacktestResult, Transaction, PortfolioHolding
from app.services.backtest_engine import BacktestEngine
from app import db

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
    'end_date': fields.String(required=True, description='结束日期')
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

    @ns.expect(backtest_create_model)
    @ns.marshal_with(backtest_model)
    @jwt_required()
    def post(self):
        """发起回测"""
        user_id = int(get_jwt_identity())
        data = request.get_json()

        # 验证投资组合是否属于当前用户
        portfolio = Portfolio.query.filter_by(
            id=data['portfolio_id'],
            user_id=user_id
        ).first()

        if not portfolio:
            return {'message': '投资组合不存在'}, 404

        try:
            # 执行回测
            engine = BacktestEngine()
            result = engine.run_backtest(
                portfolio_id=data['portfolio_id'],
                start_date=data['start_date'],
                end_date=data['end_date'],
                name=data.get('name')
            )

            return result.to_dict(), 201

        except Exception as e:
            import traceback
            error_msg = f'回测执行失败: {str(e)}'
            print(f"回测错误详情: {traceback.format_exc()}")
            return {'message': error_msg}, 500

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