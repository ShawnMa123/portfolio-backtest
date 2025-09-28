#!/usr/bin/env python3
"""
修复WARP代理池问题并测试
"""
import subprocess
import sys
import time

def install_requirements():
    """安装缺失的依赖"""
    print("🔧 安装SOCKS依赖...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install",
            "requests[socks]==2.31.0", "PySocks==1.7.1"
        ])
        print("✅ SOCKS依赖安装完成")
        return True
    except Exception as e:
        print(f"❌ 依赖安装失败: {e}")
        return False

def test_socks_connection():
    """测试SOCKS代理连接"""
    print("🌐 测试SOCKS代理连接...")

    try:
        import requests

        # 测试每个代理端口
        proxy_ports = [40001, 40002, 40003, 40004, 40005]
        working_proxies = []

        for port in proxy_ports:
            try:
                proxies = {
                    'http': f'socks5://localhost:{port}',
                    'https': f'socks5://localhost:{port}'
                }

                # 测试连接
                response = requests.get(
                    'https://httpbin.org/ip',
                    proxies=proxies,
                    timeout=10
                )

                if response.status_code == 200:
                    ip_info = response.json()
                    print(f"✅ 代理 localhost:{port} 工作正常，IP: {ip_info.get('origin', 'unknown')}")
                    working_proxies.append(port)
                else:
                    print(f"❌ 代理 localhost:{port} 响应异常: {response.status_code}")

            except Exception as e:
                print(f"❌ 代理 localhost:{port} 连接失败: {e}")

        print(f"📊 工作正常的代理: {len(working_proxies)}/{len(proxy_ports)}")
        return len(working_proxies) > 0

    except ImportError:
        print("❌ requests库未安装")
        return False
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        return False

def test_proxy_pool():
    """测试代理池功能"""
    print("🔍 测试代理池...")

    try:
        # 添加项目根目录到Python路径
        import os
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        from app.utils.proxy_pool import get_proxy_pool

        # 获取代理池实例
        pool = get_proxy_pool()

        # 强制健康检查
        print("🔧 执行健康检查...")
        pool.force_health_check()

        # 等待健康检查完成
        time.sleep(5)

        # 获取状态
        status = pool.get_pool_status()
        print(f"📊 代理池状态:")
        print(f"   总代理数: {status['total_proxies']}")
        print(f"   健康代理数: {status['healthy_proxies']}")
        print(f"   健康率: {status['health_rate']:.2%}")

        # 测试获取代理
        proxy = pool.get_next_proxy()
        if proxy:
            print(f"✅ 成功获取代理: {proxy.host}:{proxy.port}")
            return True
        else:
            print("❌ 无法获取可用代理")
            return False

    except Exception as e:
        print(f"❌ 代理池测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_data_service():
    """测试数据服务使用代理"""
    print("📊 测试数据服务...")

    try:
        # 添加项目根目录到Python路径
        import os
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        from app.services.data_service import DataService

        # 创建数据服务实例
        service = DataService()

        # 测试获取股票信息
        print("🔍 测试获取TSLA股票信息...")
        info = service.get_instrument_info('TSLA')

        if info and info.get('name') != 'TSLA':  # 如果获取到了真实名称
            print(f"✅ 成功获取股票信息: {info['name']}")
            return True
        else:
            print("⚠️ 获取到默认信息，可能使用了模拟数据")
            return False

    except Exception as e:
        print(f"❌ 数据服务测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_warp_containers():
    """检查WARP容器状态"""
    print("🐳 检查WARP容器状态...")

    try:
        # 检查容器是否运行
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=warp-proxy", "--format", "table {{.Names}}\\t{{.Status}}"],
            capture_output=True, text=True
        )

        if result.returncode == 0:
            output = result.stdout.strip()
            if output:
                print("WARP容器状态:")
                print(output)

                # 统计运行中的容器
                lines = output.split('\n')[1:]  # 跳过标题行
                running_count = len([line for line in lines if 'Up' in line])
                total_count = len(lines)

                print(f"📊 运行状态: {running_count}/{total_count}")
                return running_count > 0
            else:
                print("❌ 没有找到WARP容器")
                return False
        else:
            print(f"❌ Docker命令失败: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ 检查容器状态失败: {e}")
        return False

def start_warp_containers():
    """启动WARP容器"""
    print("🚀 启动WARP容器...")

    try:
        result = subprocess.run(
            ["docker-compose", "-f", "docker-compose.warp.yml", "up", "-d"],
            capture_output=True, text=True
        )

        if result.returncode == 0:
            print("✅ WARP容器启动命令执行成功")
            print("⏱️ 等待容器初始化...")
            time.sleep(30)  # 等待初始化
            return True
        else:
            print(f"❌ 启动失败: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ 启动异常: {e}")
        return False

def main():
    """主函数"""
    print("🔧 WARP代理池问题修复和测试")
    print("="*50)

    success_count = 0
    total_tests = 0

    # 1. 安装依赖
    total_tests += 1
    if install_requirements():
        success_count += 1

    # 2. 检查WARP容器
    total_tests += 1
    containers_running = check_warp_containers()
    if containers_running:
        success_count += 1
    else:
        print("⚠️ WARP容器未运行，尝试启动...")
        if start_warp_containers():
            containers_running = check_warp_containers()
            if containers_running:
                success_count += 1

    # 3. 测试SOCKS连接
    if containers_running:
        total_tests += 1
        if test_socks_connection():
            success_count += 1

        # 4. 测试代理池
        total_tests += 1
        if test_proxy_pool():
            success_count += 1

        # 5. 测试数据服务
        total_tests += 1
        if test_data_service():
            success_count += 1

    # 总结
    print("\n" + "="*50)
    print(f"🎯 测试完成: {success_count}/{total_tests} 成功")

    if success_count == total_tests:
        print("🎉 所有测试通过！WARP代理池工作正常")
        print("\n💡 现在可以启动应用:")
        print("   python app.py")
        print("\n🧪 运行完整测试:")
        print("   python test_warp_proxy.py")
    else:
        print("⚠️ 部分测试失败，请检查以下内容:")
        print("1. Docker是否正常运行")
        print("2. WARP容器是否启动成功")
        print("3. 网络连接是否正常")
        print("\n🔧 故障排除:")
        print("   docker-compose -f docker-compose.warp.yml logs")

    return success_count == total_tests

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)