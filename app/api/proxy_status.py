"""
代理池状态监控API
"""
from flask import request
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required
from app.utils.proxy_pool import get_proxy_pool
from app.utils.logging_config import get_logger

logger = get_logger(__name__)
ns = Namespace('proxy', description='代理池管理接口')

# API 模型定义
proxy_info_model = ns.model('ProxyInfo', {
    'key': fields.String(description='代理标识'),
    'is_healthy': fields.Boolean(description='是否健康'),
    'response_time': fields.Float(description='响应时间(秒)'),
    'error_count': fields.Integer(description='错误次数'),
    'success_count': fields.Integer(description='成功次数'),
    'last_check': fields.String(description='最后检查时间'),
    'last_used': fields.String(description='最后使用时间')
})

proxy_pool_status_model = ns.model('ProxyPoolStatus', {
    'total_proxies': fields.Integer(description='总代理数'),
    'healthy_proxies': fields.Integer(description='健康代理数'),
    'unhealthy_proxies': fields.Integer(description='不健康代理数'),
    'health_rate': fields.Float(description='健康率'),
    'proxies': fields.List(fields.Nested(proxy_info_model), description='代理详情')
})

@ns.route('/pool/status')
class ProxyPoolStatus(Resource):
    @ns.marshal_with(proxy_pool_status_model)
    @jwt_required()
    def get(self):
        """获取代理池状态"""
        logger.info("查询代理池状态")

        try:
            pool = get_proxy_pool()
            status = pool.get_pool_status()
            return status
        except Exception as e:
            logger.error(f"获取代理池状态失败: {e}")
            return {
                'error': str(e),
                'total_proxies': 0,
                'healthy_proxies': 0,
                'unhealthy_proxies': 0,
                'health_rate': 0.0,
                'proxies': []
            }, 500

@ns.route('/pool/health-check')
class ProxyPoolHealthCheck(Resource):
    @jwt_required()
    def post(self):
        """强制执行代理池健康检查"""
        logger.info("强制执行代理池健康检查")

        try:
            pool = get_proxy_pool()
            pool.force_health_check()

            return {
                'message': '健康检查已完成',
                'status': 'success'
            }, 200
        except Exception as e:
            logger.error(f"强制健康检查失败: {e}")
            return {
                'message': f'健康检查失败: {str(e)}',
                'status': 'error'
            }, 500

@ns.route('/test')
class ProxyTest(Resource):
    def get(self):
        """测试代理池功能（无需认证）"""
        logger.info("测试代理池功能")

        try:
            pool = get_proxy_pool()

            # 测试获取代理
            proxy = pool.get_next_proxy()
            if proxy:
                return {
                    'message': '代理池正常工作',
                    'proxy_used': f"{proxy.host}:{proxy.port}",
                    'proxy_healthy': proxy.is_healthy,
                    'total_healthy': len(pool.get_healthy_proxies()),
                    'status': 'success'
                }, 200
            else:
                return {
                    'message': '没有可用的健康代理',
                    'total_healthy': 0,
                    'status': 'warning'
                }, 200

        except Exception as e:
            logger.error(f"代理池测试失败: {e}")
            return {
                'message': f'代理池测试失败: {str(e)}',
                'status': 'error'
            }, 500