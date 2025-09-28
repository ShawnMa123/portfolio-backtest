#!/usr/bin/env python3
"""
生成正确的密码hash
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from werkzeug.security import generate_password_hash

def generate_demo_password():
    """生成demo用户的密码hash"""
    password = "password123"
    password_hash = generate_password_hash(password)

    print("Demo用户密码信息:")
    print(f"密码: {password}")
    print(f"Hash: {password_hash}")
    print()
    print("SQL插入语句:")
    print(f"INSERT INTO users (username, email, password_hash, full_name) VALUES ('demo', 'demo@example.com', '{password_hash}', 'Demo User');")

if __name__ == "__main__":
    generate_demo_password()