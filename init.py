"""
应用初始化模块

负责服务端完整的初始化流程，采用分层初始化检查架构：

初始化层级（按优先级排序）：
1. 核心层 (core): 最基础的环境变量，不依赖任何其他配置
   - LANGIT_SECURITY_SECRET_KEY: JWT安全密钥
   - LANGIT_APP_DEBUG: 调试模式标志

2. 数据库层 (database): 数据库相关配置
   - DATABASE_URL: 数据库连接URL
   - LANGIT_STRESS_TEST: 压力测试模式标志

3. 应用层 (app): FastAPI应用配置（预留）

4. 服务层 (service): 各种服务初始化（预留）

安全要求：
- 所有敏感配置必须通过环境变量设置
- 不再自动生成或写入敏感配置到 config.toml
- 环境变量检查为最高优先级，缺失时立即失败

使用示例:
    from init import init_app
    
    # 初始化应用
    if init_app():
        print("初始化成功")
    else:
        print("初始化失败")
"""
import os
import sys
from typing import Any, Dict, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum, auto

# 尝试加载 .env 文件（如果存在）
# 在导入其他模块之前加载，确保环境变量可用
try:
    from dotenv import load_dotenv
    load_dotenv(encoding='utf-8')
except ImportError:
    pass  # python-dotenv 未安装，跳过


class InitStage(Enum):
    """初始化阶段枚举"""
    CORE = auto()      # 核心层
    DATABASE = auto()  # 数据库层
    APP = auto()       # 应用层
    SERVICE = auto()   # 服务层


@dataclass
class EnvVarConfig:
    """环境变量配置定义"""
    name: str                      # 环境变量名称
    description: str               # 变量描述
    example: str                   # 示例值
    required: bool = True          # 是否必需
    sensitive: bool = False        # 是否为敏感信息（不在日志中显示）


@dataclass
class InitLayer:
    """初始化层定义"""
    name: str                      # 层级名称
    stage: InitStage               # 初始化阶段
    env_vars: List[EnvVarConfig]   # 该层需要的环境变量
    init_func: Optional[Callable] = None  # 该层的初始化函数（可选）
    description: str = ""          # 层级描述


# ============================================
# 环境变量配置定义（新增变量只需在这里添加）
# ============================================

# 核心层环境变量
CORE_ENV_VARS = [
    EnvVarConfig(
        name="LANGIT_SECURITY_SECRET_KEY",
        description="JWT安全密钥，用于令牌签名和验证",
        example="your-secret-key-here",
        sensitive=True
    ),
    EnvVarConfig(
        name="LANGIT_APP_DEBUG",
        description="调试模式标志，'true'启用调试，'false'为生产模式",
        example="true"
    ),
]

# 数据库层环境变量
DATABASE_ENV_VARS = [
    EnvVarConfig(
        name="DATABASE_URL",
        description="数据库连接URL",
        example="sqlite:///./langit.db 或 postgresql://user:pass@localhost/dbname"
    ),
    EnvVarConfig(
        name="LANGIT_STRESS_TEST",
        description="压力测试模式标志，'true'启用压力测试优化",
        example="false"
    ),
]

# 初始化层定义列表（按优先级排序）
INIT_LAYERS: List[InitLayer] = [
    InitLayer(
        name="核心层",
        stage=InitStage.CORE,
        env_vars=CORE_ENV_VARS,
        description="基础安全配置，不依赖其他模块"
    ),
    InitLayer(
        name="数据库层",
        stage=InitStage.DATABASE,
        env_vars=DATABASE_ENV_VARS,
        description="数据库连接配置"
    ),
]


class EnvVarChecker:
    """环境变量检查器"""
    
    @staticmethod
    def check_layer(layer: InitLayer) -> tuple[bool, List[str]]:
        """
        检查单个初始化层的环境变量
        
        Args:
            layer: 初始化层定义
            
        Returns:
            tuple: (是否全部通过, 缺失的变量名列表)
        """
        missing = []
        for env_var in layer.env_vars:
            if env_var.required and not os.environ.get(env_var.name):
                missing.append(env_var.name)
        return len(missing) == 0, missing
    
    @staticmethod
    def print_error_report(layers_with_missing: List[tuple[InitLayer, List[str]]]) -> None:
        """
        打印环境变量缺失错误报告
        
        Args:
            layers_with_missing: 包含缺失变量的层列表
        """
        print("=" * 70)
        print("错误：缺少必需的环境变量")
        print("=" * 70)
        
        for layer, missing_vars in layers_with_missing:
            print(f"\n【{layer.name}】")
            print(f"  描述: {layer.description}")
            print("  缺失变量:")
            for var_name in missing_vars:
                # 查找变量配置
                var_config = next(
                    (v for v in layer.env_vars if v.name == var_name), 
                    None
                )
                if var_config:
                    print(f"    - {var_config.name}")
                    print(f"      说明: {var_config.description}")
                    print(f"      示例: {var_config.example}")
                else:
                    print(f"    - {var_name}")
        
        print("\n" + "=" * 70)
        print("请通过以下方式之一设置环境变量：")
        print("")
        print("  1. 使用 Tauri Client 启动服务端（推荐）")
        print("     Client 会自动注入所需的环境变量")
        print("")
        print("  2. 手动设置环境变量（PowerShell）：")
        
        # 生成示例命令
        for layer in INIT_LAYERS:
            for var in layer.env_vars:
                if var.sensitive:
                    print(f"     $env:{var.name} = 'your-{var.name.lower().replace('_', '-')}-here'")
                else:
                    print(f"     $env:{var.name} = '{var.example}'")
        
        print("")
        print("  3. 使用 .env 文件（需要 python-dotenv）：")
        print("     pip install python-dotenv")
        print("     在项目根目录创建 .env 文件，包含：")
        
        for layer in INIT_LAYERS:
            for var in layer.env_vars:
                if var.sensitive:
                    print(f"     {var.name}=your-secret-value")
                else:
                    print(f"     {var.name}={var.example}")
        
        print("")
        print("安全提示：")
        print("  - JWT Secret Key 应该是一串随机的安全字符串")
        print("  - 在生产环境中，请确保使用强密钥并妥善保管")
        print("  - 不要将该密钥提交到版本控制")
        print("=" * 70)


class AppInitializer:
    """应用初始化器，负责服务端完整的初始化流程"""

    def __init__(self, config_path: str = "config.toml"):
        self.config_path = config_path
        self.config_manager = None
        self._utils_config_manager = None
        self._logger = None
        self._checker = EnvVarChecker()

    def _check_all_env_vars(self) -> bool:
        """
        检查所有初始化层的环境变量
        
        Returns:
            bool: 所有必需环境变量都存在返回True，否则返回False
        """
        layers_with_missing = []
        
        for layer in INIT_LAYERS:
            passed, missing = self._checker.check_layer(layer)
            if not passed:
                layers_with_missing.append((layer, missing))
        
        if layers_with_missing:
            self._checker.print_error_report(layers_with_missing)
            return False
        
        return True

    def _init_imports(self) -> bool:
        """
        延迟导入依赖模块
        
        在确认环境变量已设置后，才导入可能触发数据库配置加载的模块
        
        Returns:
            bool: 导入是否成功
        """
        try:
            from config import ConfigManager
            from utils.config_utils import generate_default_config, write_config_file, get_config_manager
            from utils.logging import init_logging, get_logger
            
            self.config_manager = ConfigManager(self.config_path)
            self._utils_config_manager = get_config_manager(self.config_path)
            self._logger = get_logger("init")
            return True
        except ValueError as e:
            # 数据库配置错误
            print("=" * 70)
            print("数据库配置错误")
            print("=" * 70)
            print(str(e))
            print("=" * 70)
            return False
        except Exception as e:
            print(f"导入依赖模块时发生错误: {e}")
            return False

    def _gen_default_config(self) -> Dict[str, Any]:
        """生成默认配置"""
        from utils.config_utils import generate_default_config
        return generate_default_config()

    def _write_config(self, config_data: Dict[str, Any]) -> None:
        """写入配置文件"""
        from utils.config_utils import write_config_file
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
            except Exception as e:
                self._logger.warning(f"配置文件验证失败: {e}，重新生成默认配置")
                default_config = self._gen_default_config()
                self._write_config(default_config)
        return True

    def _init_secret_key(self) -> bool:
        """检查 JWT Secret Key 是否已设置"""
        secret_key = os.environ.get("LANGIT_SECURITY_SECRET_KEY")
        if secret_key:
            return True
        else:
            self._logger.error("安全密钥检查失败")
            return False

    def _init_database(self, create_test_data: bool = False) -> bool:
        """初始化数据库"""
        from utils.init_database import init_database
        
        config = self.config_manager.get_config()
        should_create_test_data = create_test_data or config.app.debug

        if init_database(create_test_data=should_create_test_data):
            return True
        else:
            self._logger.error("数据库初始化失败")
            return False

    def _init_repository_root(self) -> bool:
        """初始化仓库根目录"""
        from utils.git_utils import ensure_repository_root
        
        try:
            ensure_repository_root()
            return True
        except Exception as e:
            self._logger.error(f"仓库根目录初始化失败: {e}")
            return False

    def _init_logging(self) -> bool:
        """初始化日志系统"""
        from utils.logging import init_logging
        
        try:
            init_logging(
                log_dir="logs",
                app_name="langit",
                level="info",
                console_output=True,
                use_date_directory=True,
                separate_error_log=True,
                websocket_output=True
            )
            return True
        except Exception as e:
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

        初始化顺序：
        1. 环境变量检查（最高优先级）
        2. 延迟导入依赖模块
        3. 配置文件初始化
        4. 日志系统初始化
        5. 安全密钥检查
        6. 数据库初始化
        7. 仓库目录初始化
        8. 服务端口检查

        Args:
            check_service: 是否检查并终止占用端口的服务
            init_db: 是否初始化数据库
            create_test_data: 是否创建测试数据（仅开发环境）

        Returns:
            bool: 初始化是否全部成功
        """
        # ========== 阶段 0: 环境变量检查（最高优先级） ==========
        if not self._check_all_env_vars():
            return False
        
        # ========== 阶段 1: 延迟导入依赖模块 ==========
        if not self._init_imports():
            return False

        # ========== 阶段 2: 配置文件 ==========
        if not self._init_config():
            return False

        # ========== 阶段 3: 日志系统 ==========
        if not self._init_logging():
            return False

        # ========== 阶段 4: 安全密钥 ==========
        if not self._init_secret_key():
            return False

        # ========== 阶段 5: 数据库 ==========
        if init_db:
            if not self._init_database(create_test_data=create_test_data):
                return False

        # ========== 阶段 6: 仓库目录 ==========
        if not self._init_repository_root():
            return False

        # ========== 阶段 7: 服务端口检查 ==========
        if check_service:
            self._check_service_port()

        self._logger.info("应用初始化完成")
        return True

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
        from utils.port_utils import check_and_terminate_running_service as _check_and_terminate_service
        return _check_and_terminate_service(port=port, config_path=self.config_path)

    def terminate_all_python_services(self, port: Optional[int] = None) -> int:
        """终止所有 Python 服务"""
        from utils.port_utils import terminate_all_python_services as _terminate_all_services
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


def get_required_env_vars() -> List[str]:
    """
    获取所有必需的环境变量名称列表
    
    Returns:
        List[str]: 环境变量名称列表
    """
    return [
        var.name
        for layer in INIT_LAYERS
        for var in layer.env_vars
        if var.required
    ]


def print_env_var_guide() -> None:
    """打印环境变量配置指南"""
    print("=" * 70)
    print("环境变量配置指南")
    print("=" * 70)
    
    for layer in INIT_LAYERS:
        print(f"\n【{layer.name}】")
        print(f"  描述: {layer.description}")
        print("  必需变量:")
        for var in layer.env_vars:
            if var.required:
                print(f"    - {var.name}")
                print(f"      说明: {var.description}")
                print(f"      示例: {var.example}")
    
    print("\n" + "=" * 70)
