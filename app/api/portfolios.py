from flask import request
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import Portfolio, PortfolioConfiguration, Instrument
from app import db

ns = Namespace('portfolios', description='投资组合相关接口')

# API 模型定义
portfolio_model = ns.model('Portfolio', {
    'id': fields.Integer(description='组合ID'),
    'user_id': fields.Integer(description='用户ID'),
    'name': fields.String(description='组合名称'),
    'description': fields.String(description='组合描述'),
    'initial_capital': fields.Float(description='初始资金'),
    'currency': fields.String(description='货币'),
    'status': fields.String(description='状态'),
    'created_at': fields.String(description='创建时间'),
    'updated_at': fields.String(description='更新时间')
})

portfolio_create_model = ns.model('PortfolioCreate', {
    'name': fields.String(required=True, description='组合名称'),
    'description': fields.String(description='组合描述'),
    'initial_capital': fields.Float(required=True, description='初始资金'),
    'currency': fields.String(description='货币', default='USD')
})

configuration_model = ns.model('PortfolioConfiguration', {
    'id': fields.Integer(description='配置ID'),
    'portfolio_id': fields.Integer(description='组合ID'),
    'instrument_id': fields.Integer(description='标的ID'),
    'instrument': fields.Nested(ns.model('InstrumentInfo', {
        'id': fields.Integer(),
        'symbol': fields.String(),
        'name': fields.String(),
        'type': fields.String()
    })),
    'weight': fields.Float(description='权重'),
    'investment_frequency': fields.String(description='投资频率'),
    'frequency_detail': fields.Raw(description='频率详情'),
    'transaction_fee_rate': fields.Float(description='手续费率'),
    'buy_type': fields.String(description='买入类型'),
    'buy_amount': fields.Float(description='买入金额'),
    'buy_quantity': fields.Integer(description='买入数量'),
    'start_date': fields.String(description='开始日期'),
    'end_date': fields.String(description='结束日期'),
    'is_active': fields.Boolean(description='是否激活')
})

configuration_create_model = ns.model('ConfigurationCreate', {
    'instrument_id': fields.Integer(required=True, description='标的ID'),
    'weight': fields.Float(description='权重'),
    'investment_frequency': fields.String(required=True, description='投资频率'),
    'frequency_detail': fields.Raw(description='频率详情'),
    'transaction_fee_rate': fields.Float(description='手续费率', default=0.0003),
    'buy_type': fields.String(required=True, description='买入类型'),
    'buy_amount': fields.Float(description='买入金额'),
    'buy_quantity': fields.Integer(description='买入数量'),
    'start_date': fields.String(required=True, description='开始日期'),
    'end_date': fields.String(description='结束日期')
})

@ns.route('')
class PortfolioList(Resource):
    @ns.marshal_list_with(portfolio_model)
    @jwt_required()
    def get(self):
        """获取用户投资组合列表"""
        user_id = int(get_jwt_identity())
        portfolios = Portfolio.query.filter_by(user_id=user_id).order_by(Portfolio.created_at.desc()).all()
        return [portfolio.to_dict() for portfolio in portfolios]

    @ns.expect(portfolio_create_model)
    @ns.marshal_with(portfolio_model)
    @jwt_required()
    def post(self):
        """创建投资组合"""
        user_id = int(get_jwt_identity())
        data = request.get_json()

        portfolio = Portfolio(
            user_id=user_id,
            name=data['name'],
            description=data.get('description'),
            initial_capital=data['initial_capital'],
            currency=data.get('currency', 'USD')
        )

        db.session.add(portfolio)
        db.session.commit()

        return portfolio.to_dict(), 201

@ns.route('/<int:portfolio_id>')
class PortfolioDetail(Resource):
    @ns.marshal_with(portfolio_model)
    @jwt_required()
    def get(self, portfolio_id):
        """获取投资组合详情"""
        user_id = int(get_jwt_identity())
        portfolio = Portfolio.query.filter_by(id=portfolio_id, user_id=user_id).first()

        if not portfolio:
            return {'message': '投资组合不存在'}, 404

        return portfolio.to_dict()

    @ns.expect(ns.model('PortfolioUpdate', {
        'name': fields.String(description='组合名称'),
        'description': fields.String(description='组合描述'),
        'status': fields.String(description='状态')
    }))
    @ns.marshal_with(portfolio_model)
    @jwt_required()
    def put(self, portfolio_id):
        """更新投资组合"""
        user_id = int(get_jwt_identity())
        portfolio = Portfolio.query.filter_by(id=portfolio_id, user_id=user_id).first()

        if not portfolio:
            return {'message': '投资组合不存在'}, 404

        data = request.get_json()

        if 'name' in data:
            portfolio.name = data['name']
        if 'description' in data:
            portfolio.description = data['description']
        if 'status' in data:
            portfolio.status = data['status']

        db.session.commit()

        return portfolio.to_dict()

    @jwt_required()
    def delete(self, portfolio_id):
        """删除投资组合"""
        user_id = int(get_jwt_identity())
        portfolio = Portfolio.query.filter_by(id=portfolio_id, user_id=user_id).first()

        if not portfolio:
            return {'message': '投资组合不存在'}, 404

        db.session.delete(portfolio)
        db.session.commit()

        return {'message': '投资组合已删除'}, 200

@ns.route('/<int:portfolio_id>/configurations')
class PortfolioConfigurationList(Resource):
    @ns.marshal_list_with(configuration_model)
    @jwt_required()
    def get(self, portfolio_id):
        """获取投资组合配置"""
        user_id = int(get_jwt_identity())
        portfolio = Portfolio.query.filter_by(id=portfolio_id, user_id=user_id).first()

        if not portfolio:
            return {'message': '投资组合不存在'}, 404

        configurations = PortfolioConfiguration.query.filter_by(
            portfolio_id=portfolio_id,
            is_active=True
        ).all()

        return [config.to_dict() for config in configurations]

    @ns.expect(configuration_create_model)
    @ns.marshal_with(configuration_model)
    @jwt_required()
    def post(self, portfolio_id):
        """添加投资组合配置"""
        user_id = int(get_jwt_identity())
        portfolio = Portfolio.query.filter_by(id=portfolio_id, user_id=user_id).first()

        if not portfolio:
            return {'message': '投资组合不存在'}, 404

        data = request.get_json()

        # 验证标的是否存在
        instrument = Instrument.query.get(data['instrument_id'])
        if not instrument:
            return {'message': '投资标的不存在'}, 404

        # 验证买入类型和参数
        if data['buy_type'] == 'AMOUNT' and not data.get('buy_amount'):
            return {'message': '按金额买入时必须指定买入金额'}, 400
        if data['buy_type'] == 'QUANTITY' and not data.get('buy_quantity'):
            return {'message': '按数量买入时必须指定买入数量'}, 400

        # 检查是否已存在相同标的的配置
        existing_config = PortfolioConfiguration.query.filter_by(
            portfolio_id=portfolio_id,
            instrument_id=data['instrument_id'],
            is_active=True
        ).first()

        if existing_config:
            return {'message': '该标的已存在配置'}, 400

        from datetime import datetime
        config = PortfolioConfiguration(
            portfolio_id=portfolio_id,
            instrument_id=data['instrument_id'],
            weight=data.get('weight'),
            investment_frequency=data['investment_frequency'],
            frequency_detail=data.get('frequency_detail'),
            transaction_fee_rate=data.get('transaction_fee_rate', 0.0003),
            buy_type=data['buy_type'],
            buy_amount=data.get('buy_amount'),
            buy_quantity=data.get('buy_quantity'),
            start_date=datetime.strptime(data['start_date'], '%Y-%m-%d').date(),
            end_date=datetime.strptime(data['end_date'], '%Y-%m-%d').date() if data.get('end_date') else None
        )

        db.session.add(config)
        db.session.commit()

        return config.to_dict(), 201

@ns.route('/<int:portfolio_id>/configurations/<int:config_id>')
class PortfolioConfigurationDetail(Resource):
    @ns.marshal_with(configuration_model)
    @jwt_required()
    def get(self, portfolio_id, config_id):
        """获取配置详情"""
        user_id = int(get_jwt_identity())
        portfolio = Portfolio.query.filter_by(id=portfolio_id, user_id=user_id).first()

        if not portfolio:
            return {'message': '投资组合不存在'}, 404

        config = PortfolioConfiguration.query.filter_by(
            id=config_id,
            portfolio_id=portfolio_id
        ).first()

        if not config:
            return {'message': '配置不存在'}, 404

        return config.to_dict()

    @ns.expect(ns.model('ConfigurationUpdate', {
        'weight': fields.Float(description='权重'),
        'investment_frequency': fields.String(description='投资频率'),
        'frequency_detail': fields.Raw(description='频率详情'),
        'transaction_fee_rate': fields.Float(description='手续费率'),
        'buy_type': fields.String(description='买入类型'),
        'buy_amount': fields.Float(description='买入金额'),
        'buy_quantity': fields.Integer(description='买入数量'),
        'start_date': fields.String(description='开始日期'),
        'end_date': fields.String(description='结束日期'),
        'is_active': fields.Boolean(description='是否激活')
    }))
    @ns.marshal_with(configuration_model)
    @jwt_required()
    def put(self, portfolio_id, config_id):
        """更新配置"""
        user_id = int(get_jwt_identity())
        portfolio = Portfolio.query.filter_by(id=portfolio_id, user_id=user_id).first()

        if not portfolio:
            return {'message': '投资组合不存在'}, 404

        config = PortfolioConfiguration.query.filter_by(
            id=config_id,
            portfolio_id=portfolio_id
        ).first()

        if not config:
            return {'message': '配置不存在'}, 404

        data = request.get_json()

        # 更新字段
        for field in ['weight', 'investment_frequency', 'frequency_detail', 'transaction_fee_rate',
                     'buy_type', 'buy_amount', 'buy_quantity', 'is_active']:
            if field in data:
                setattr(config, field, data[field])

        if 'start_date' in data:
            from datetime import datetime
            config.start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()

        if 'end_date' in data:
            from datetime import datetime
            config.end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date() if data['end_date'] else None

        db.session.commit()

        return config.to_dict()

    @jwt_required()
    def delete(self, portfolio_id, config_id):
        """删除配置"""
        user_id = int(get_jwt_identity())
        portfolio = Portfolio.query.filter_by(id=portfolio_id, user_id=user_id).first()

        if not portfolio:
            return {'message': '投资组合不存在'}, 404

        config = PortfolioConfiguration.query.filter_by(
            id=config_id,
            portfolio_id=portfolio_id
        ).first()

        if not config:
            return {'message': '配置不存在'}, 404

        db.session.delete(config)
        db.session.commit()

        return {'message': '配置已删除'}, 200