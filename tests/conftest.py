"""
Pytest配置文件

添加项目根目录到Python路径，使测试能够导入项目模块
"""
import sys
import os

# 将项目根目录添加到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
