"""
应用初始化模块

负责服务端完整的初始化流程，包括：
1. 配置文件生成/验证
2. 数据库初始化
3. 仓库根目录创建
4. 端口冲突检查
5. JWT Secret Key 生成
"""
import os
from typing import Any, Dict, Optional

from config import ConfigManager

from utils.config_utils import generate_default_config, write_config_file, get_config_manager
from utils.init_database import init_database
from utils.git_utils import ensure_repository_root
from utils.port_utils import (
    check_and_terminate_running_service as _check_and_terminate_service,
    terminate_all_python_services as _terminate_all_services,
)
from utils.logging_utils import ensure_log_dir, init_async_logging, get_async_logger, shutdown_async_logging


class AppInitializer:
    """应用初始化器，负责服务端完整的初始化流程"""

    def __init__(self, config_path: str = "config.toml"):
        self.config_path = config_path
        self.config_manager = ConfigManager(config_path)
        self._utils_config_manager = get_config_manager(config_path)
        self._logger = get_async_logger("init")

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
        """初始化配置文件"""
        if not os.path.exists(self.config_path):
            self._logger.info(f"配置文件不存在，生成默认配置: {self.config_path}")
            default_config = self._gen_default_config()
            self._write_config(default_config)
        else:
            try:
                self.config_manager.get_config(force_reload=True)
                self._logger.debug("配置文件验证通过")
            except Exception as e:
                self._logger.warning(f"配置文件验证失败: {e}，重新生成默认配置")
                default_config = self._gen_default_config()
                self._write_config(default_config)
        return True

    def _init_secret_key(self) -> bool:
        """初始化 JWT Secret Key"""
        secret_key = self._utils_config_manager.ensure_secret_key()
        if secret_key:
            self._logger.debug("安全密钥已就绪")
            return True
        else:
            self._logger.error("安全密钥检查失败")
            return False

    def _init_database(self, create_test_data: bool = False) -> bool:
        """初始化数据库"""
        # 根据 debug 配置决定是否创建测试数据
        config = self.config_manager.get_config()
        should_create_test_data = create_test_data or config.app.debug

        if init_database(create_test_data=should_create_test_data):
            self._logger.info("数据库初始化完成")
            return True
        else:
            self._logger.error("数据库初始化失败")
            return False

    def _init_repository_root(self) -> bool:
        """初始化仓库根目录"""
        try:
            repo_root = ensure_repository_root()
            self._logger.info(f"仓库根目录: {repo_root}")
            return True
        except Exception as e:
            self._logger.error(f"仓库根目录初始化失败: {e}")
            return False

    def _init_logging(self) -> bool:
        """初始化日志目录和异步日志系统"""
        try:
            log_dir = ensure_log_dir()
            init_async_logging(
                log_dir=str(log_dir),
                app_name="langit",
                level="info",
                console_output=True
            )
            self._logger.info(f"日志目录: {log_dir}")
            self._logger.info("异步日志系统已启动")
            return True
        except Exception as e:
            # 使用 print 因为日志可能还未初始化
            print(f"日志初始化失败: {e}")
            return False

    def _check_service_port(self) -> bool:
        """检查并终止占用端口的服务"""
        return self.check_and_terminate_running_service()

    def initialize(
        self,
        check_service: bool = True,
        init_db: bool = True,
        create_test_data: bool = False,
    ) -> bool:
        """
        执行完整初始化流程

        Args:
            check_service: 是否检查并终止占用端口的服务
            init_db: 是否初始化数据库
            create_test_data: 是否创建测试数据（仅开发环境）

        Returns:
            bool: 初始化是否全部成功
        """
        try:
            # 步骤 1: 配置文件
            if not self._init_config():
                return False

            # 步骤 2: 日志系统（优先初始化，后续步骤可以使用日志）
            if not self._init_logging():
                return False

            # 步骤 3: 安全密钥
            if not self._init_secret_key():
                return False

            # 步骤 4: 数据库
            if init_db:
                if not self._init_database(create_test_data=create_test_data):
                    return False

            # 步骤 5: 仓库目录
            if not self._init_repository_root():
                return False

            # 步骤 6: 服务端口检查
            if check_service:
                self._check_service_port()

            self._logger.info("应用初始化完成")
            return True

        except Exception as e:
            self._logger.error(f"初始化过程中发生错误: {e}")
            return False

    def reset_config(self) -> None:
        """重置配置为默认值"""
        self._logger.info(f"重置配置文件: {self.config_path}")
        default_config = self._gen_default_config()
        self._write_config(default_config)
        self.config_manager.get_config(force_reload=True)

    def update_config(self, new_config: Dict[str, Any]) -> None:
        """更新配置"""
        self._logger.info(f"更新配置文件: {self.config_path}")
        self.config_manager.update_config(new_config)

    def check_and_terminate_running_service(self, port: Optional[int] = None) -> bool:
        """检查并终止占用端口的服务"""
        return _check_and_terminate_service(port=port, config_path=self.config_path)

    def terminate_all_python_services(self, port: Optional[int] = None) -> int:
        """终止所有 Python 服务"""
        return _terminate_all_services(port=port, config_path=self.config_path)


# 创建全局初始化器实例
initializer = AppInitializer()


def init_app(
    check_service: bool = True,
    init_db: bool = True,
    create_test_data: bool = False,
) -> bool:
    """
    初始化应用的便捷函数

    Args:
        check_service: 是否检查并终止占用端口的服务
        init_db: 是否初始化数据库
        create_test_data: 是否创建测试数据

    Returns:
        bool: 初始化是否成功
    """
    return initializer.initialize(
        check_service=check_service,
        init_db=init_db,
        create_test_data=create_test_data,
    )


def reset_config() -> None:
    """重置配置为默认值"""
    initializer.reset_config()


def update_config(new_config: Dict[str, Any]) -> None:
    """更新配置"""
    initializer.update_config(new_config)


def check_and_terminate_running_service(port: Optional[int] = None) -> bool:
    """检查并终止占用端口的服务"""
    return initializer.check_and_terminate_running_service(port)


def terminate_all_python_services(port: Optional[int] = None) -> int:
    """终止所有 Python 服务"""
    return initializer.terminate_all_python_services(port)
