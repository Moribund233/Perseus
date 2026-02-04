import os

from typing import Optional, Dict, Any
from config import ConfigManager

from utils.config_utils import generate_default_config, write_config_file
from utils.port_utils import (
    check_and_terminate_running_service,
    terminate_all_python_services,
)


class Initializer:
    def __init__(self, config_path: str = "config.toml"):
        self.config_path = config_path
        self.config_manager = ConfigManager(config_path)

    def _gen_default_config(self) -> Dict[str, Any]:
        return generate_default_config()

    def _write_config(self, config_data: Dict[str, Any]) -> None:
        try:
            write_config_file(config_data, self.config_path)
        except IOError as e:
            raise RuntimeError(f"写入配置文件失败: {e}")

    def initialize(self, check_service: bool = True) -> None:
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

        if check_service:
            print("\n=== 服务生命周期检查 ===")
            self.check_and_terminate_running_service()
            print("=== 检查完成 ===\n")

    def reset_config(self) -> None:
        print(f"正在重置配置文件 {self.config_path}...")
        default_config = self._gen_default_config()
        self._write_config(default_config)
        self.config_manager.get_config(force_reload=True)
        print(f"配置文件已重置为默认值：{self.config_path}")

    def update_config(self, new_config: Dict[str, Any]) -> None:
        print(f"正在更新配置文件 {self.config_path}...")
        self.config_manager.update_config(new_config)
        print(f"配置文件已更新：{self.config_path}")

    def check_and_terminate_running_service(self, port: Optional[int] = None) -> bool:
        return check_and_terminate_running_service(port=port, config_path=self.config_path)

    def terminate_all_python_services(self, port: Optional[int] = None) -> int:
        return terminate_all_python_services(port=port, config_path=self.config_path)


initializer = Initializer()


def init_app(check_service: bool = True) -> None:
    initializer.initialize(check_service=check_service)


def reset_config() -> None:
    initializer.reset_config()


def update_config(new_config: Dict[str, Any]) -> None:
    initializer.update_config(new_config)


if __name__ == "__main__":
    init_app()
