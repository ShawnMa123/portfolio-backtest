from flask import request, jsonify
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.models import User
from app import db

ns = Namespace('auth', description='用户认证相关接口')

# API 模型定义
register_model = ns.model('UserRegister', {
    'username': fields.String(required=True, description='用户名'),
    'password': fields.String(required=True, description='密码'),
    'email': fields.String(required=True, description='邮箱'),
    'full_name': fields.String(description='全名')
})

login_model = ns.model('UserLogin', {
    'username': fields.String(required=True, description='用户名'),
    'password': fields.String(required=True, description='密码')
})

user_model = ns.model('User', {
    'id': fields.Integer(description='用户ID'),
    'username': fields.String(description='用户名'),
    'email': fields.String(description='邮箱'),
    'full_name': fields.String(description='全名'),
    'timezone': fields.String(description='时区'),
    'created_at': fields.String(description='创建时间'),
    'is_active': fields.Boolean(description='是否激活')
})

@ns.route('/register')
class UserRegister(Resource):
    @ns.expect(register_model)
    def post(self):
        """用户注册"""
        data = request.get_json()

        # 检查用户名是否已存在
        if User.query.filter_by(username=data['username']).first():
            return {'message': '用户名已存在'}, 400

        # 检查邮箱是否已存在
        if User.query.filter_by(email=data['email']).first():
            return {'message': '邮箱已存在'}, 400

        # 创建新用户
        user = User(
            username=data['username'],
            email=data['email'],
            full_name=data.get('full_name')
        )
        user.set_password(data['password'])

        db.session.add(user)
        db.session.commit()

        return {'message': '注册成功', 'user_id': user.id}, 201

@ns.route('/login')
class UserLogin(Resource):
    @ns.expect(login_model)
    def post(self):
        """用户登录"""
        data = request.get_json()

        user = User.query.filter_by(username=data['username']).first()

        if user and user.check_password(data['password']) and user.is_active:
            access_token = create_access_token(identity=str(user.id))
            return {
                'access_token': access_token,
                'user': user.to_dict()
            }, 200

        return {'message': '用户名或密码错误'}, 401

@ns.route('/profile')
class UserProfile(Resource):
    @ns.marshal_with(user_model)
    @jwt_required()
    def get(self):
        """获取用户信息"""
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)

        if not user:
            return {'message': '用户不存在'}, 404

        return user.to_dict()

    @ns.expect(ns.model('UserUpdate', {
        'email': fields.String(description='邮箱'),
        'full_name': fields.String(description='全名'),
        'timezone': fields.String(description='时区')
    }))
    @jwt_required()
    def put(self):
        """更新用户信息"""
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)

        if not user:
            return {'message': '用户不存在'}, 404

        data = request.get_json()

        if 'email' in data and data['email'] != user.email:
            if User.query.filter_by(email=data['email']).first():
                return {'message': '邮箱已存在'}, 400
            user.email = data['email']

        if 'full_name' in data:
            user.full_name = data['full_name']

        if 'timezone' in data:
            user.timezone = data['timezone']

        db.session.commit()

        return user.to_dict()