#!/usr/bin/env python3
"""
生产环境监控脚本
"""
import subprocess
import requests
import time
import json
import sys
from datetime import datetime
from pathlib import Path

class SystemMonitor:
    """系统监控器"""

    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.project_root = Path(__file__).parent.parent

    def check_app_health(self):
        """检查应用健康状态"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                return True, data
            else:
                return False, f"HTTP {response.status_code}"
        except Exception as e:
            return False, str(e)

    def check_proxy_pool(self):
        """检查代理池状态"""
        try:
            response = requests.get(f"{self.base_url}/api/proxy/test", timeout=10)
            if response.status_code == 200:
                data = response.json()
                return True, data
            else:
                return False, f"HTTP {response.status_code}"
        except Exception as e:
            return False, str(e)

    def check_docker_containers(self):
        """检查Docker容器状态"""
        try:
            result = subprocess.run([
                "docker", "ps", "--filter", "name=warp-proxy",
                "--format", "{{.Names}}:{{.Status}}"
            ], capture_output=True, text=True)

            if result.returncode == 0:
                containers = {}
                for line in result.stdout.strip().split('\n'):
                    if ':' in line:
                        name, status = line.split(':', 1)
                        containers[name] = 'healthy' if 'Up' in status else 'unhealthy'
                return True, containers
            else:
                return False, result.stderr
        except Exception as e:
            return False, str(e)

    def check_system_resources(self):
        """检查系统资源"""
        try:
            # 内存使用
            mem_result = subprocess.run(
                ["free", "-h"], capture_output=True, text=True
            )

            # 磁盘使用
            disk_result = subprocess.run(
                ["df", "-h", "/"], capture_output=True, text=True
            )

            resources = {
                'memory': mem_result.stdout if mem_result.returncode == 0 else 'N/A',
                'disk': disk_result.stdout if disk_result.returncode == 0 else 'N/A'
            }

            return True, resources
        except Exception as e:
            return False, str(e)

    def generate_report(self):
        """生成监控报告"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'checks': {}
        }

        # 应用健康检查
        print("🔍 检查应用健康状态...")
        success, data = self.check_app_health()
        report['checks']['app_health'] = {
            'status': 'healthy' if success else 'unhealthy',
            'data': data
        }
        print(f"   {'✅' if success else '❌'} 应用状态: {data}")

        # 代理池检查
        print("🌐 检查代理池状态...")
        success, data = self.check_proxy_pool()
        report['checks']['proxy_pool'] = {
            'status': 'healthy' if success else 'unhealthy',
            'data': data
        }
        if success:
            healthy_proxies = data.get('total_healthy', 0)
            print(f"   ✅ 代理池状态: {healthy_proxies} 个健康代理")
        else:
            print(f"   ❌ 代理池状态: {data}")

        # Docker容器检查
        print("🐳 检查Docker容器...")
        success, data = self.check_docker_containers()
        report['checks']['docker_containers'] = {
            'status': 'healthy' if success else 'unhealthy',
            'data': data
        }
        if success:
            healthy_count = sum(1 for status in data.values() if status == 'healthy')
            total_count = len(data)
            print(f"   ✅ 容器状态: {healthy_count}/{total_count} 健康")
            for name, status in data.items():
                icon = "✅" if status == 'healthy' else "❌"
                print(f"     {icon} {name}: {status}")
        else:
            print(f"   ❌ 容器检查失败: {data}")

        # 系统资源检查
        print("📊 检查系统资源...")
        success, data = self.check_system_resources()
        report['checks']['system_resources'] = {
            'status': 'info',
            'data': data
        }

        return report

    def continuous_monitor(self, interval: int = 60):
        """持续监控"""
        print(f"🔄 开始持续监控 (间隔: {interval}秒)")
        print("按 Ctrl+C 停止监控")

        try:
            while True:
                print(f"\n{'='*60}")
                print(f"⏰ 监控时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print('='*60)

                report = self.generate_report()

                # 保存报告
                reports_dir = self.project_root / "logs" / "monitoring"
                reports_dir.mkdir(parents=True, exist_ok=True)

                report_file = reports_dir / f"monitor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(report_file, 'w') as f:
                    json.dump(report, f, indent=2, ensure_ascii=False)

                print(f"📄 报告已保存: {report_file}")

                # 检查是否有异常
                unhealthy_services = []
                for service, check in report['checks'].items():
                    if check['status'] == 'unhealthy':
                        unhealthy_services.append(service)

                if unhealthy_services:
                    print(f"\n🚨 发现异常服务: {', '.join(unhealthy_services)}")
                    # 可以在这里添加告警逻辑
                else:
                    print("\n✅ 所有服务正常")

                print(f"\n⏱️ {interval}秒后进行下次检查...")
                time.sleep(interval)

        except KeyboardInterrupt:
            print("\n👋 监控已停止")

    def alert_check(self):
        """告警检查"""
        report = self.generate_report()

        alerts = []

        # 检查应用健康
        if report['checks']['app_health']['status'] == 'unhealthy':
            alerts.append("应用无法访问")

        # 检查代理池
        proxy_check = report['checks']['proxy_pool']
        if proxy_check['status'] == 'unhealthy':
            alerts.append("代理池不可用")
        elif proxy_check['status'] == 'healthy':
            healthy_proxies = proxy_check['data'].get('total_healthy', 0)
            if healthy_proxies < 2:
                alerts.append(f"健康代理数量不足: {healthy_proxies}")

        # 检查容器
        container_check = report['checks']['docker_containers']
        if container_check['status'] == 'unhealthy':
            alerts.append("Docker容器检查失败")
        else:
            containers = container_check['data']
            unhealthy_containers = [name for name, status in containers.items()
                                  if status != 'healthy']
            if unhealthy_containers:
                alerts.append(f"不健康的容器: {', '.join(unhealthy_containers)}")

        return alerts

def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="系统监控脚本")
    parser.add_argument("--url", default="http://localhost:5000",
                       help="应用URL")
    parser.add_argument("--monitor", action="store_true",
                       help="持续监控模式")
    parser.add_argument("--interval", type=int, default=60,
                       help="监控间隔（秒）")
    parser.add_argument("--alert", action="store_true",
                       help="仅检查告警")

    args = parser.parse_args()

    monitor = SystemMonitor(args.url)

    if args.alert:
        alerts = monitor.alert_check()
        if alerts:
            print("🚨 发现以下问题:")
            for alert in alerts:
                print(f"  ❌ {alert}")
            sys.exit(1)
        else:
            print("✅ 系统运行正常")
            sys.exit(0)
    elif args.monitor:
        monitor.continuous_monitor(args.interval)
    else:
        monitor.generate_report()

if __name__ == "__main__":
    main()