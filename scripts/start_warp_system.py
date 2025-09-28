#!/usr/bin/env python3
"""
WARP代理池系统一键启动脚本
"""
import subprocess
import time
import requests
import sys
import os

def run_command(command, description, check_output=False):
    """执行命令并处理结果"""
    print(f"🔧 {description}...")
    try:
        if check_output:
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"❌ {description}失败: {result.stderr}")
                return False, result.stderr
            return True, result.stdout
        else:
            result = subprocess.run(command, shell=True)
            if result.returncode != 0:
                print(f"❌ {description}失败")
                return False, ""
            return True, ""
    except Exception as e:
        print(f"❌ {description}异常: {e}")
        return False, str(e)

def check_docker():
    """检查Docker是否安装并运行"""
    print("🐳 检查Docker环境...")
    success, output = run_command("docker --version", "检查Docker版本", check_output=True)
    if not success:
        print("❌ Docker未安装或未运行")
        print("💡 请安装Docker Desktop: https://www.docker.com/products/docker-desktop")
        return False

    print(f"✅ Docker版本: {output.strip()}")

    success, output = run_command("docker-compose --version", "检查Docker Compose版本", check_output=True)
    if not success:
        print("❌ Docker Compose未安装")
        return False

    print(f"✅ Docker Compose版本: {output.strip()}")
    return True

def start_warp_proxies():
    """启动WARP代理池"""
    print("🚀 启动WARP代理池...")

    # 检查配置文件是否存在
    if not os.path.exists("docker-compose.warp.yml"):
        print("❌ 未找到 docker-compose.warp.yml 文件")
        return False

    # 启动WARP代理池
    success, _ = run_command(
        "docker-compose -f docker-compose.warp.yml up -d",
        "启动WARP代理容器"
    )

    if not success:
        return False

    print("⏱️ 等待WARP代理初始化（预计需要1-2分钟）...")
    time.sleep(30)  # 等待代理启动

    return True

def check_warp_status():
    """检查WARP代理状态"""
    print("📊 检查WARP代理状态...")

    # 检查容器状态
    success, output = run_command(
        "docker ps --filter name=warp-proxy --format 'table {{.Names}}\\t{{.Status}}'",
        "检查WARP容器状态",
        check_output=True
    )

    if success:
        print("WARP容器状态:")
        print(output)

    # 检查端口
    ports_to_check = [40001, 40002, 40003, 40004, 40005]
    healthy_ports = []

    for port in ports_to_check:
        try:
            # 简单的端口连接测试
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('localhost', port))
            sock.close()

            if result == 0:
                healthy_ports.append(port)
                print(f"✅ 端口 {port}: 可访问")
            else:
                print(f"❌ 端口 {port}: 不可访问")
        except Exception as e:
            print(f"❌ 端口 {port}: 检查异常 {e}")

    return len(healthy_ports) > 0

def start_redis():
    """检查并启动Redis（如果需要）"""
    print("🔴 检查Redis状态...")

    try:
        import redis
        # 尝试连接到代理池Redis
        client = redis.from_url("redis://localhost:6380/0", decode_responses=True)
        client.ping()
        print("✅ 代理池Redis已运行")
        return True
    except:
        print("⚠️ 代理池Redis未运行，将通过Docker启动")
        # Redis会通过docker-compose.warp.yml一起启动
        return True

def start_application():
    """启动应用程序"""
    print("📱 准备启动应用程序...")

    # 检查Python依赖
    try:
        import yfinance
        import redis
        import celery
        print("✅ Python依赖检查通过")
    except ImportError as e:
        print(f"❌ 缺少Python依赖: {e}")
        print("💡 请运行: pip install -r requirements.txt")
        return False

    print("🎯 应用程序准备就绪!")
    print()
    print("请在单独的终端中运行以下命令:")
    print("1. 启动Celery Worker:")
    print("   python celery_worker.py")
    print()
    print("2. 启动Flask应用:")
    print("   python app.py")
    print()
    print("3. 运行测试:")
    print("   python test_warp_proxy.py")

    return True

def test_system():
    """测试系统功能"""
    print("🧪 测试系统功能...")

    # 等待用户启动应用
    print("请确保已启动Flask应用，然后按Enter继续测试...")
    input()

    try:
        # 测试健康检查
        response = requests.get("http://localhost:5000/health", timeout=5)
        if response.status_code == 200:
            print("✅ Flask应用健康检查通过")
        else:
            print(f"❌ Flask应用健康检查失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 无法连接到Flask应用: {e}")
        print("💡 请确保已启动Flask应用 (python app.py)")
        return False

    try:
        # 测试代理池
        response = requests.get("http://localhost:5000/api/proxy/test", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 代理池测试: {data['message']}")
            return True
        else:
            print(f"❌ 代理池测试失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 代理池测试异常: {e}")
        return False

def show_monitoring_info():
    """显示监控信息"""
    print("\n" + "="*60)
    print("📊 系统监控信息")
    print("="*60)

    print("\n🔍 实用命令:")
    print("# 查看WARP容器状态")
    print("docker ps | grep warp")
    print()
    print("# 查看WARP容器日志")
    print("docker logs warp-proxy-1")
    print()
    print("# 重启代理池")
    print("docker-compose -f docker-compose.warp.yml restart")
    print()
    print("# 停止代理池")
    print("docker-compose -f docker-compose.warp.yml down")
    print()
    print("# 查看Redis代理状态")
    print("docker exec -it redis-proxy-pool redis-cli keys 'proxy:*'")

    print("\n🌐 API端点:")
    print("http://localhost:5000/api/docs/          # Swagger文档")
    print("http://localhost:5000/health             # 健康检查")
    print("http://localhost:5000/api/proxy/test     # 代理池测试")

    print("\n📈 监控面板:")
    print("可以考虑集成以下监控工具:")
    print("- Flower: Celery任务监控")
    print("- Grafana: 系统指标可视化")
    print("- Prometheus: 指标收集")

def main():
    """主函数"""
    print("🚀 WARP代理池系统一键启动")
    print("="*50)

    # 1. 检查环境
    if not check_docker():
        return False

    # 2. 启动WARP代理池
    if not start_warp_proxies():
        return False

    # 3. 检查WARP状态
    if not check_warp_status():
        print("⚠️ 部分WARP代理可能未正常启动")
        print("💡 可以继续，系统会自动处理不健康的代理")

    # 4. 检查Redis
    start_redis()

    # 5. 准备应用程序
    if not start_application():
        return False

    # 6. 显示后续步骤
    show_monitoring_info()

    print(f"\n🎉 WARP代理池系统启动完成!")
    print("系统已准备就绪，可以开始处理Yahoo Finance API请求。")

    # 询问是否运行测试
    test_choice = input("\n是否运行系统测试? (y/N): ").lower()
    if test_choice == 'y':
        test_system()

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)