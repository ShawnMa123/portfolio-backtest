#!/usr/bin/env python3
"""
Scripts包初始化文件
提供通用的路径配置函数
"""
import sys
from pathlib import Path

def setup_project_path():
    """
    将项目根目录添加到Python路径
    这样scripts目录中的脚本就可以导入app模块了
    """
    project_root = Path(__file__).parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    return project_root