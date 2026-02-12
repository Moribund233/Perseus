"""
应用初始化模块

负责服务端完整的初始化流程，包括：
1. 配置文件生成/验证
2. 数据库初始化
3. 仓库根目录创建
4. Nginx 配置生成（可选）
5. 端口冲突检查
6. JWT Secret Key 生成
"""
import os
from typing import Any, Dict, Optional

from config import ConfigManager

from utils.config_utils import generate_default_config, write_config_file, get_config_manager
from utils.init_database import init_database
from utils.git_utils import ensure_repository_root
from utils.nginx_config import get_nginx_config_generator
from utils.port_utils import (
    check_and_terminate_running_service,
    terminate_all_python_services,
)


class AppInitializer:
    """
    应用初始化器

    负责服务端完整的初始化流程
    """

    def __init__(self, config_path: str = "config.toml"):
        """
        初始化应用初始化器

        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.config_manager = ConfigManager(config_path)
        self._utils_config_manager = get_config_manager(config_path)

    def _gen_default_config(self) -> Dict[str, Any]:
        """生成默认配置"""
        return generate_default_config()

    def _write_config(self, config_data: Dict[str, Any]) -> None:
        """写入配置文件"""
        try:
            write_config_file(config_data, self.config_path)
        except IOError as e:
            raise RuntimeError(f"写入配置文件失败: {e}")

    def _init_config(self) -> bool:
        """
        初始化配置文件

        Returns:
            bool: 初始化是否成功
        """
        if not os.path.exists(self.config_path):
            print(f"配置文件 {self.config_path} 不存在，正在生成默认配置...")
            default_config = self._gen_default_config()
            self._write_config(default_config)
            print(f"默认配置文件已生成：{self.config_path}")
        else:
            print(f"配置文件 {self.config_path} 已存在")
            try:
                self.config_manager.get_config(force_reload=True)
                print("配置文件结构验证通过")
            except Exception as e:
                print(f"配置文件结构验证失败：{e}")
                print("正在重新生成默认配置文件...")
                default_config = self._gen_default_config()
                self._write_config(default_config)
                print(f"默认配置文件已重新生成：{self.config_path}")
        return True

    def _init_secret_key(self) -> bool:
        """
        初始化 JWT Secret Key

        Returns:
            bool: 初始化是否成功
        """
        print("正在检查安全密钥...")
        secret_key = self._utils_config_manager.ensure_secret_key()
        if secret_key:
            print("安全密钥已就绪")
            return True
        else:
            print("安全密钥检查失败")
            return False

    def _init_database(self, create_test_data: bool = False) -> bool:
        """
        初始化数据库

        Args:
            create_test_data: 是否创建测试数据

        Returns:
            bool: 初始化是否成功
        """
        print("正在初始化数据库...")
        if init_database(create_test_data=create_test_data):
            print("数据库初始化完成")
            return True
        else:
            print("数据库初始化失败")
            return False

    def _init_repository_root(self) -> bool:
        """
        初始化仓库根目录

        Returns:
            bool: 初始化是否成功
        """
        print("正在初始化仓库存储目录...")
        try:
            repo_root = ensure_repository_root()
            print(f"仓库根目录已确保存在: {repo_root}")
            return True
        except Exception as e:
            print(f"仓库根目录初始化失败: {e}")
            return False

    def _init_nginx_config(self) -> bool:
        """
        初始化 Nginx 配置

        Returns:
            bool: 初始化是否成功
        """
        print("正在初始化 Nginx 配置...")
        try:
            nginx_config = self._utils_config_manager.get_nginx_config()

            # 检查 Nginx 是否启用
            if not nginx_config.get("enabled", True):
                print("Nginx 已禁用，跳过配置生成")
                return True

            # 获取安装路径和配置路径
            install_path = nginx_config.get("install_path", "nginx")
            config_path = nginx_config.get("config_path")

            # 确保 install_path 是绝对路径
            if install_path:
                install_path = os.path.abspath(install_path)

            # 创建配置生成器
            nginx_generator = get_nginx_config_generator(config_path, install_path)

            # 生成配置
            if nginx_generator.generate_config(nginx_config):
                print(f"Nginx 配置文件已生成: {nginx_generator.get_config_path()}")
                return True
            else:
                print("Nginx 配置文件生成失败")
                return False

        except Exception as e:
            print(f"Nginx 配置初始化失败: {e}")
            return False

    def _check_service_port(self) -> bool:
        """
        检查并终止占用端口的服务

        Returns:
            bool: 检查是否通过
        """
        print("\n=== 服务生命周期检查 ===")
        result = self.check_and_terminate_running_service()
        print("=== 检查完成 ===\n")
        return result

    def initialize(
        self,
        check_service: bool = True,
        init_db: bool = True,
        init_nginx: bool = False,
        create_test_data: bool = False,
    ) -> bool:
        """
        执行完整初始化流程

        Args:
            check_service: 是否检查并终止占用端口的服务
            init_db: 是否初始化数据库
            init_nginx: 是否生成 Nginx 配置
            create_test_data: 是否创建测试数据（仅开发环境）

        Returns:
            bool: 初始化是否全部成功
        """
        try:
            # 步骤 1: 配置文件
            if not self._init_config():
                return False

            # 步骤 2: 安全密钥
            self._init_secret_key()

            # 步骤 3: 数据库
            if init_db:
                if not self._init_database(create_test_data=create_test_data):
                    return False

            # 步骤 4: 仓库目录
            if not self._init_repository_root():
                return False

            # 步骤 5: Nginx 配置（可选）
            if init_nginx:
                self._init_nginx_config()

            # 步骤 6: 服务端口检查
            if check_service:
                self._check_service_port()

            print("=" * 50)
            print("应用初始化完成")
            print("=" * 50)
            return True

        except Exception as e:
            print(f"初始化过程中发生错误: {e}")
            return False

    def reset_config(self) -> None:
        """重置配置为默认值"""
        print(f"正在重置配置文件 {self.config_path}...")
        default_config = self._gen_default_config()
        self._write_config(default_config)
        self.config_manager.get_config(force_reload=True)
        print(f"配置文件已重置为默认值：{self.config_path}")

    def update_config(self, new_config: Dict[str, Any]) -> None:
        """更新配置"""
        print(f"正在更新配置文件 {self.config_path}...")
        self.config_manager.update_config(new_config)
        print(f"配置文件已更新：{self.config_path}")

    def check_and_terminate_running_service(self, port: Optional[int] = None) -> bool:
        """检查并终止占用端口的服务"""
        return check_and_terminate_running_service(port=port, config_path=self.config_path)

    def terminate_all_python_services(self, port: Optional[int] = None) -> int:
        """终止所有 Python 服务"""
        return terminate_all_python_services(port=port, config_path=self.config_path)


# 创建全局初始化器实例
initializer = AppInitializer()


def init_app(
    check_service: bool = True,
    init_db: bool = True,
    init_nginx: bool = False,
    create_test_data: bool = False,
) -> bool:
    """
    初始化应用的便捷函数

    Args:
        check_service: 是否检查并终止占用端口的服务
        init_db: 是否初始化数据库
        init_nginx: 是否生成 Nginx 配置
        create_test_data: 是否创建测试数据

    Returns:
        bool: 初始化是否成功
    """
    return initializer.initialize(
        check_service=check_service,
        init_db=init_db,
        init_nginx=init_nginx,
        create_test_data=create_test_data,
    )


def reset_config() -> None:
    """重置配置为默认值"""
    initializer.reset_config()


def update_config(new_config: Dict[str, Any]) -> None:
    """更新配置"""
    initializer.update_config(new_config)


if __name__ == "__main__":
    # 开发环境可以启用测试数据创建
    init_app(create_test_data=True)
