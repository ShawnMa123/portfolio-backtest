from flask import Blueprint
from flask_restx import Api

api_bp = Blueprint('api', __name__)
api = Api(api_bp, doc='/docs/', title='Portfolio Backtest API', version='1.0', description='ETF/股票回测系统API')

from app.api.auth import ns as auth_ns
from app.api.instruments import ns as instruments_ns
from app.api.portfolios import ns as portfolios_ns
from app.api.backtests import ns as backtests_ns
from app.api.proxy_status import ns as proxy_ns

api.add_namespace(auth_ns, path='/auth')
api.add_namespace(instruments_ns, path='/instruments')
api.add_namespace(portfolios_ns, path='/portfolios')
api.add_namespace(backtests_ns, path='/backtests')
api.add_namespace(proxy_ns, path='/proxy')