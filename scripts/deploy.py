#!/usr/bin/env python3
"""
生产环境部署脚本
"""
import subprocess
import sys
import os
import time
import argparse
from pathlib import Path

class ProductionDeployer:
    """生产环境部署器"""

    def __init__(self, env: str = "production"):
        self.env = env
        self.project_root = Path(__file__).parent.parent
        self.compose_file = self.project_root / "docker-compose.warp.yml"

    def check_requirements(self):
        """检查部署要求"""
        print("🔍 检查部署环境...")

        # 检查Docker
        try:
            result = subprocess.run(["docker", "--version"],
                                  capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception("Docker未安装")
            print(f"✅ Docker: {result.stdout.strip()}")
        except Exception as e:
            print(f"❌ Docker检查失败: {e}")
            return False

        # 检查Docker Compose
        try:
            result = subprocess.run(["docker-compose", "--version"],
                                  capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception("Docker Compose未安装")
            print(f"✅ Docker Compose: {result.stdout.strip()}")
        except Exception as e:
            print(f"❌ Docker Compose检查失败: {e}")
            return False

        # 检查配置文件
        if not self.compose_file.exists():
            print(f"❌ 未找到配置文件: {self.compose_file}")
            return False
        print(f"✅ 配置文件: {self.compose_file}")

        return True

    def setup_environment(self):
        """设置环境变量"""
        print("⚙️ 设置环境变量...")

        env_file = self.project_root / ".env"

        if not env_file.exists():
            print("📝 创建 .env 文件...")
            env_content = f"""
# 环境配置
FLASK_ENV={self.env}
USE_PROXY_POOL=true
PROXY_RATE_LIMIT=1.5
PROXY_HEALTH_CHECK_INTERVAL=60

# 数据库配置
DATABASE_URL=postgresql://postgres:password@localhost:5432/portfolio_backtest

# Redis配置
REDIS_URL=redis://localhost:6379/0
PROXY_POOL_REDIS_URL=redis://localhost:6380/0

# Celery配置
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# 安全配置
SECRET_KEY={os.urandom(32).hex()}
JWT_SECRET_KEY={os.urandom(32).hex()}

# 外部API配置
ALPHA_VANTAGE_API_KEY=your_api_key_here
""".strip()

            with open(env_file, 'w') as f:
                f.write(env_content)

            print(f"✅ 已创建 {env_file}")
            print("⚠️ 请编辑 .env 文件设置正确的配置值")
        else:
            print(f"✅ 环境文件已存在: {env_file}")

    def install_dependencies(self):
        """安装Python依赖"""
        print("📦 安装Python依赖...")

        requirements_file = self.project_root / "requirements.txt"
        if not requirements_file.exists():
            print(f"❌ 未找到 requirements.txt")
            return False

        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
            ])
            print("✅ Python依赖安装完成")
            return True
        except Exception as e:
            print(f"❌ 依赖安装失败: {e}")
            return False

    def deploy_warp_proxies(self):
        """部署WARP代理池"""
        print("🌐 部署WARP代理池...")

        try:
            # 停止现有容器
            subprocess.run([
                "docker-compose", "-f", str(self.compose_file), "down"
            ], cwd=self.project_root)

            # 启动新容器
            result = subprocess.run([
                "docker-compose", "-f", str(self.compose_file), "up", "-d"
            ], cwd=self.project_root, capture_output=True, text=True)

            if result.returncode != 0:
                raise Exception(f"容器启动失败: {result.stderr}")

            print("✅ WARP代理池部署成功")
            print("⏱️ 等待代理初始化...")
            time.sleep(60)  # 等待代理初始化

            return True
        except Exception as e:
            print(f"❌ WARP部署失败: {e}")
            return False

    def verify_deployment(self):
        """验证部署"""
        print("🔍 验证部署状态...")

        # 检查容器状态
        try:
            result = subprocess.run([
                "docker", "ps", "--filter", "name=warp-proxy",
                "--format", "table {{.Names}}\\t{{.Status}}"
            ], capture_output=True, text=True)

            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]  # 跳过标题
                running_count = len([line for line in lines if 'Up' in line])
                total_count = len(lines)

                print(f"📊 WARP容器状态: {running_count}/{total_count} 运行中")

                if running_count < 3:  # 至少3个代理运行
                    print("⚠️ 运行的代理数量较少，可能影响性能")
                    return False
                else:
                    print("✅ 代理池运行正常")
                    return True
            else:
                print("❌ 无法检查容器状态")
                return False

        except Exception as e:
            print(f"❌ 验证失败: {e}")
            return False

    def create_systemd_service(self):
        """创建systemd服务（Linux）"""
        if os.name != 'posix':
            print("⚠️ 非Linux系统，跳过systemd服务创建")
            return True

        print("🔧 创建systemd服务...")

        service_content = f"""[Unit]
Description=Portfolio Backtest API
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=root
WorkingDirectory={self.project_root}
Environment=FLASK_ENV={self.env}
ExecStart={sys.executable} app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""

        try:
            service_file = "/etc/systemd/system/portfolio-backtest.service"
            with open(service_file, 'w') as f:
                f.write(service_content)

            # 重新加载systemd
            subprocess.run(["systemctl", "daemon-reload"])
            subprocess.run(["systemctl", "enable", "portfolio-backtest"])

            print(f"✅ 已创建systemd服务: {service_file}")
            return True
        except Exception as e:
            print(f"⚠️ 创建systemd服务失败: {e}")
            return False

    def deploy(self):
        """执行完整部署"""
        print("🚀 开始生产环境部署")
        print("="*50)

        steps = [
            ("检查部署要求", self.check_requirements),
            ("设置环境变量", self.setup_environment),
            ("安装Python依赖", self.install_dependencies),
            ("部署WARP代理池", self.deploy_warp_proxies),
            ("验证部署状态", self.verify_deployment),
            ("创建系统服务", self.create_systemd_service),
        ]

        success_count = 0

        for step_name, step_func in steps:
            print(f"\n🔄 {step_name}...")
            try:
                if step_func():
                    success_count += 1
                    print(f"✅ {step_name} 完成")
                else:
                    print(f"❌ {step_name} 失败")
                    break
            except Exception as e:
                print(f"❌ {step_name} 异常: {e}")
                break

        print(f"\n📊 部署结果: {success_count}/{len(steps)} 步骤成功")

        if success_count == len(steps):
            print("\n🎉 生产环境部署成功！")
            self.show_next_steps()
            return True
        else:
            print("\n❌ 部署失败，请检查上述错误")
            return False

    def show_next_steps(self):
        """显示后续步骤"""
        print("\n📋 后续步骤:")
        print("1. 启动应用:")
        print(f"   cd {self.project_root}")
        print("   python app.py")
        print("\n2. 启动Celery Worker:")
        print("   python scripts/celery_worker.py")
        print("\n3. 运行测试:")
        print("   python tests/test_warp_proxy.py")
        print("\n4. 访问API文档:")
        print("   http://your-server:5000/api/docs/")
        print("\n5. 监控服务:")
        print("   systemctl status portfolio-backtest")
        print("   docker ps | grep warp")
        print("\n6. 查看日志:")
        print("   tail -f logs/app.jsonl")
        print("   docker logs warp-proxy-1")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="生产环境部署脚本")
    parser.add_argument("--env", default="production",
                       choices=["production", "staging", "development"],
                       help="部署环境")
    parser.add_argument("--verify-only", action="store_true",
                       help="仅验证当前部署状态")

    args = parser.parse_args()

    deployer = ProductionDeployer(args.env)

    if args.verify_only:
        success = deployer.verify_deployment()
    else:
        success = deployer.deploy()

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()