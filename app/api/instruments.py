from flask import request
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required
from app.models import Instrument
from app.services.data_service import DataService
from app import db

ns = Namespace('instruments', description='投资标的相关接口')

# API 模型定义
instrument_model = ns.model('Instrument', {
    'id': fields.Integer(description='标的ID'),
    'symbol': fields.String(description='股票代码'),
    'name': fields.String(description='标的名称'),
    'type': fields.String(description='类型'),
    'exchange': fields.String(description='交易所'),
    'currency': fields.String(description='货币'),
    'sector': fields.String(description='行业'),
    'description': fields.String(description='描述'),
    'is_active': fields.Boolean(description='是否激活')
})

@ns.route('')
class InstrumentList(Resource):
    @ns.marshal_list_with(instrument_model)
    @jwt_required()
    def get(self):
        """获取投资标的列表"""
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '')

        query = Instrument.query.filter_by(is_active=True)

        if search:
            query = query.filter(
                db.or_(
                    Instrument.symbol.ilike(f'%{search}%'),
                    Instrument.name.ilike(f'%{search}%')
                )
            )

        instruments = query.paginate(
            page=page, per_page=per_page, error_out=False
        )

        return [instrument.to_dict() for instrument in instruments.items]

@ns.route('/search')
class InstrumentSearch(Resource):
    @jwt_required()
    def get(self):
        """搜索投资标的"""
        symbol = request.args.get('symbol', '').upper()

        if not symbol:
            return {'message': '请提供股票代码'}, 400

        # 先从数据库查找
        instrument = Instrument.query.filter_by(symbol=symbol, is_active=True).first()

        if instrument:
            return instrument.to_dict()

        # 如果数据库中没有，从外部API获取
        data_service = DataService()
        try:
            info = data_service.get_instrument_info(symbol)

            # 创建新的标的记录
            instrument = Instrument(
                symbol=info['symbol'],
                name=info['name'],
                type=info['type'],
                exchange=info['exchange'],
                currency=info['currency'],
                sector=info.get('sector'),
                description=info.get('description')
            )

            db.session.add(instrument)
            db.session.commit()

            return instrument.to_dict()

        except Exception as e:
            return {'message': f'获取标的信息失败: {str(e)}'}, 400

@ns.route('/<string:symbol>')
class InstrumentDetail(Resource):
    @ns.marshal_with(instrument_model)
    @jwt_required()
    def get(self, symbol):
        """获取投资标的详情"""
        instrument = Instrument.query.filter_by(symbol=symbol.upper(), is_active=True).first()

        if not instrument:
            return {'message': '标的不存在'}, 404

        return instrument.to_dict()

@ns.route('/<string:symbol>/price')
class InstrumentPrice(Resource):
    @jwt_required()
    def get(self, symbol):
        """获取标的价格数据"""
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        if not start_date or not end_date:
            return {'message': '请提供开始和结束日期'}, 400

        # 检查标的是否存在
        instrument = Instrument.query.filter_by(symbol=symbol.upper(), is_active=True).first()
        if not instrument:
            return {'message': '标的不存在'}, 404

        data_service = DataService()
        try:
            price_data = data_service.get_price_data(symbol.upper(), start_date, end_date)

            if price_data.empty:
                return {'message': '未找到价格数据'}, 404

            # 转换为JSON格式
            result = []
            for index, row in price_data.iterrows():
                result.append({
                    'date': index.strftime('%Y-%m-%d') if hasattr(index, 'strftime') else str(index),
                    'open': float(row['open']),
                    'high': float(row['high']),
                    'low': float(row['low']),
                    'close': float(row['close']),
                    'volume': int(row['volume']),
                    'adj_close': float(row['adj_close'])
                })

            return {
                'symbol': symbol.upper(),
                'data': result
            }

        except Exception as e:
            return {'message': f'获取价格数据失败: {str(e)}'}, 500

@ns.route('/<string:symbol>/latest')
class InstrumentLatestPrice(Resource):
    @jwt_required()
    def get(self, symbol):
        """获取标的最新价格"""
        # 检查标的是否存在
        instrument = Instrument.query.filter_by(symbol=symbol.upper(), is_active=True).first()
        if not instrument:
            return {'message': '标的不存在'}, 404

        data_service = DataService()
        try:
            latest_price = data_service.get_latest_price(symbol.upper())

            if latest_price is None:
                return {'message': '未找到最新价格'}, 404

            return {
                'symbol': symbol.upper(),
                'price': latest_price,
                'timestamp': None  # 可以添加时间戳
            }

        except Exception as e:
            return {'message': f'获取最新价格失败: {str(e)}'}, 500