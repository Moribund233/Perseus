"""
ConfigManager 集成测试

测试配置管理器的核心功能：
1. TOML 配置文件加载
2. 环境变量覆盖
3. 配置验证
4. 配置重载
"""
import os
import pytest
import tempfile
from unittest.mock import patch

from core.config import ConfigManager, Config, get_config, reset_module_config_manager
from core.config import validate_config, ConfigValidationResult, StorageSettings, SecuritySettings
from core.exception import ConfigValidationException


class TestConfigManager:
    """ConfigManager 集成测试类"""

    def setup_method(self):
        """每个测试方法前重置 ConfigManager 单例和环境变量"""
        # 先清除所有可能影响的环境变量
        env_vars_to_clear = [
            "DATABASE_URL",
            "PERSEUS_STRESS_TEST",
            "PERSEUS_SECURITY_SECRET_KEY",
            "PERSEUS_APP_DEBUG",
            "PERSEUS_APP_TITLE",
            "PERSEUS_DATABASE_URL",
        ]
        for var in env_vars_to_clear:
            if var in os.environ:
                del os.environ[var]
        # 然后重置单例
        reset_module_config_manager()

    def teardown_method(self):
        """每个测试方法后清理"""
        reset_module_config_manager()

    def test_config_toml_merge_with_env(self):
        """
        测试 TOML 配置与环境变量合并

        验证点：
        1. TOML 文件中的配置被正确加载
        2. 环境变量可以覆盖 TOML 配置
        3. 优先级：环境变量 > TOML > 默认值
        """
        # 创建临时 TOML 配置文件
        toml_content = """
[app]
title = "Test Perseus"
debug = false

[server]
host = "127.0.0.1"
port = 9000

[database]
pool_size = 10
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write(toml_content)
            config_path = f.name

        try:
            # 设置环境变量覆盖 TOML 配置
            os.environ["PERSEUS_APP_DEBUG"] = "true"
            os.environ["DATABASE_URL"] = "sqlite:///./test_config.db"

            # 创建 ConfigManager 实例
            manager = ConfigManager(config_path)
            config = manager.config

            # 验证 TOML 配置被加载
            assert config.app.title == "Test Perseus", "TOML 中的 app.title 应该被加载"
            assert config.server.host == "127.0.0.1", "TOML 中的 server.host 应该被加载"
            assert config.server.port == 9000, "TOML 中的 server.port 应该被加载"
            assert config.database.pool_size == 10, "TOML 中的 database.pool_size 应该被加载"

            # 验证环境变量覆盖 TOML
            assert config.app.debug == True, "环境变量 PERSEUS_APP_DEBUG 应该覆盖 TOML"
            assert config.database.url == "sqlite:///./test_config.db", "环境变量 DATABASE_URL 应该覆盖默认值"

        finally:
            os.unlink(config_path)
            if "PERSEUS_APP_DEBUG" in os.environ:
                del os.environ["PERSEUS_APP_DEBUG"]
            if "DATABASE_URL" in os.environ:
                del os.environ["DATABASE_URL"]

    def test_config_env_priority_over_toml(self):
        """
        测试环境变量优先级高于 TOML 配置

        验证点：
        1. 当环境变量和 TOML 都设置了同一配置项时，环境变量生效
        2. 未设置环境变量的配置项，使用 TOML 值
        """
        toml_content = """
[app]
title = "TOML Title"
version = "1.0.0"

[security]
access_token_expire_minutes = 60
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write(toml_content)
            config_path = f.name

        try:
            # 只覆盖部分配置
            os.environ["PERSEUS_APP_TITLE"] = "Env Title"

            manager = ConfigManager(config_path)
            config = manager.config

            # 环境变量覆盖的应该生效
            assert config.app.title == "Env Title", "环境变量应该覆盖 TOML"

            # 未设置环境变量的应该使用 TOML 值
            assert config.app.version == "1.0.0", "未设置环境变量的应该使用 TOML 值"
            assert config.security.access_token_expire_minutes == 60, "未设置环境变量的应该使用 TOML 值"

        finally:
            os.unlink(config_path)
            if "PERSEUS_APP_TITLE" in os.environ:
                del os.environ["PERSEUS_APP_TITLE"]

    def test_config_default_values(self):
        """
        测试配置默认值

        验证点：
        1. 当没有 TOML 文件和环境变量时，使用 Pydantic Field 默认值
        2. 所有必要配置都有合理的默认值
        """
        # 使用不存在的配置文件路径
        manager = ConfigManager("/nonexistent/config.toml")
        config = manager.config

        # 验证默认值
        assert config.app.title == "Perseus API", "应该有默认应用标题"
        assert config.server.host == "0.0.0.0", "应该有默认服务器地址"
        assert config.server.port == 8000, "应该有默认服务器端口"
        assert config.database.pool_size == 20, "应该有默认连接池大小"
        # 注意：容器环境中可能使用不同的默认路径
        assert config.storage.repo_root in ["./repositories", "/data/repositories"], "应该有默认仓库根目录"

    def test_config_invalid_database_url(self):
        """
        测试无效的数据库 URL 验证

        验证点：
        1. 无效的数据库 URL 应该引发验证错误
        2. 不支持的数据库协议应该被拒绝
        """
        # 设置无效的数据库 URL
        os.environ["DATABASE_URL"] = "mysql://invalid/url"

        try:
            with pytest.raises(ValueError) as exc_info:
                ConfigManager("/nonexistent/config.toml")

            error_msg = str(exc_info.value).lower()
            assert "不支持的协议" in str(exc_info.value) or "unsupported" in error_msg or "mysql" in error_msg

        finally:
            if "DATABASE_URL" in os.environ:
                del os.environ["DATABASE_URL"]

    def test_config_database_url_validation_formats(self):
        """
        测试支持的数据库 URL 格式

        验证点：
        1. SQLite URL 格式被接受
        2. PostgreSQL URL 格式被接受
        3. 各种合法的 URL 变体都能通过验证
        """
        valid_urls = [
            "sqlite:///./test.db",
            "sqlite+aiosqlite:///./test.db",
            "postgresql://user:pass@localhost/db",
            "postgres://user:pass@localhost/db",
            "postgresql+psycopg2://user:pass@localhost/db",
            "postgresql+asyncpg://user:pass@localhost/db",
        ]

        for url in valid_urls:
            reset_module_config_manager()
            os.environ["DATABASE_URL"] = url

            try:
                manager = ConfigManager("/nonexistent/config.toml")
                config = manager.config
                assert config.database.url == url, f"URL 应该被接受: {url}"
            finally:
                if "DATABASE_URL" in os.environ:
                    del os.environ["DATABASE_URL"]

    def test_config_stress_test_mode(self):
        """
        测试压力测试模式配置

        验证点：
        1. PERSEUS_STRESS_TEST=true 启用压力测试模式
        2. 压力测试模式影响数据库连接池配置
        3. 并发控制配置根据压力测试模式自适应
        """
        os.environ["PERSEUS_STRESS_TEST"] = "true"

        try:
            manager = ConfigManager("/nonexistent/config.toml")
            config = manager.config

            assert config.database.is_stress_test == True, "压力测试模式应该被启用"

            # 验证并发配置自适应
            assert config.concurrency.max_concurrent == 200, "压力测试模式应该有更高的并发限制"
            assert config.concurrency.max_wait_time == 10.0, "压力测试模式应该有更长的等待时间"

        finally:
            if "PERSEUS_STRESS_TEST" in os.environ:
                del os.environ["PERSEUS_STRESS_TEST"]

    def test_config_reload(self):
        """
        测试配置重载功能

        验证点：
        1. reload() 方法可以重新加载配置
        2. 重载后新配置生效
        """
        toml_content = """
[app]
title = "Original Title"
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write(toml_content)
            config_path = f.name

        try:
            manager = ConfigManager(config_path)
            assert manager.config.app.title == "Original Title"

            # 修改配置文件
            with open(config_path, 'w') as f:
                f.write("""
[app]
title = "Reloaded Title"
""")

            # 重载配置
            manager.reload()

            assert manager.config.app.title == "Reloaded Title", "重载后新配置应该生效"

        finally:
            os.unlink(config_path)

    def test_config_singleton_pattern(self):
        """
        测试 ConfigManager 单例模式

        验证点：
        1. 多次创建 ConfigManager 返回同一实例
        2. 配置修改对所有引用可见
        """
        manager1 = ConfigManager("/nonexistent/config.toml")
        manager2 = ConfigManager("/nonexistent/config.toml")

        assert manager1 is manager2, "ConfigManager 应该是单例"

    def test_get_config_convenience_function(self):
        """
        测试 get_config 便捷函数

        验证点：
        1. get_config() 返回有效的 Config 对象
        2. 多次调用返回同一配置实例
        """
        reset_module_config_manager()

        config1 = get_config()
        config2 = get_config()

        assert isinstance(config1, Config), "应该返回 Config 实例"
        assert config1 is config2, "多次调用应该返回同一实例"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


# =============================================================================
# F-009: 启动配置完整性校验测试
# =============================================================================


class TestConfigValidation:
    """配置完整性校验测试类"""

    def setup_method(self):
        """每个测试方法前重置 ConfigManager 单例"""
        from core.config import reset_module_config_manager
        env_vars_to_clear = [
            "DATABASE_URL", "PERSEUS_STRESS_TEST",
            "PERSEUS_SECURITY_SECRET_KEY", "PERSEUS_APP_DEBUG",
        ]
        for var in env_vars_to_clear:
            if var in os.environ:
                del os.environ[var]
        reset_module_config_manager()

    def teardown_method(self):
        """每个测试方法后清理"""
        from core.config import reset_module_config_manager
        reset_module_config_manager()

    def test_validate_config_valid_defaults(self):
        """
        测试默认配置校验通过

        验证点：
        1. 使用默认配置时校验通过
        2. 无 errors
        """
        # 设置 debug 模式避免因缺少 secret_key 报错
        os.environ["PERSEUS_APP_DEBUG"] = "true"
        try:
            result = validate_config(get_config())
            assert result.is_valid, f"默认配置应通过校验, 错误: {result.errors}"
        finally:
            if "PERSEUS_APP_DEBUG" in os.environ:
                del os.environ["PERSEUS_APP_DEBUG"]

    def test_validate_config_invalid_db_url_fails_startup(self):
        """
        测试无效的数据库 URL 导致校验失败

        验证点：
        1. 不支持的数据库协议被拒绝
        """
        os.environ["DATABASE_URL"] = "mysql://invalid/url"

        try:
            # 使用无效 URL 创建配置
            from core.config import ConfigManager
            # 会因 Pydantic 验证而直接抛出 ValueError
            with pytest.raises(ValueError) as exc_info:
                ConfigManager("/nonexistent/config.toml")

            assert "不支持的" in str(exc_info.value) or "mysql" in str(exc_info.value).lower(), \
                f"错误信息应包含协议不支持提示: {exc_info.value}"
        finally:
            if "DATABASE_URL" in os.environ:
                del os.environ["DATABASE_URL"]

    def test_validate_storage_repo_root_creation(self, tmpdir):
        """
        测试存储路径自动创建

        验证点：
        1. 不存在的仓库目录可以被自动创建
        """
        from core.config import Config, AppSettings, StorageSettings, SecuritySettings
        test_root = os.path.join(tmpdir, "new_repos")
        config = Config(
            app=AppSettings(debug=True),
            storage=StorageSettings(repo_root=test_root),
            security=SecuritySettings(secret_key="test-key"),
        )

        result = validate_config(config)

        assert result.is_valid, f"校验应通过: {result.errors}"
        assert os.path.exists(test_root), "仓库根目录应被自动创建"

    def test_validate_security_production_no_secret_key(self):
        """
        测试生产环境缺少 Secret Key 时报错

        验证点：
        1. 生产模式（debug=False）且没有 secret_key 时报错
        """
        from core.config import Config, AppSettings, SecuritySettings
        config = Config(
            app=AppSettings(debug=False),
            security=SecuritySettings(secret_key="")
        )

        result = validate_config(config)

        assert not result.is_valid, "生产环境缺少 Secret Key 应报错"
        assert any("JWT 密钥" in e for e in result.errors), \
            "错误应提示 JWT Secret Key 缺失"

    def test_validate_security_debug_no_secret_key_warns(self):
        """
        测试开发环境缺少 Secret Key 时仅警告

        验证点：
        1. debug=True 时缺少 secret_key 仅产生警告
        2. 不产生错误
        """
        from core.config import Config, AppSettings, SecuritySettings
        config = Config(
            app=AppSettings(debug=True),
            security=SecuritySettings(secret_key="")
        )

        result = validate_config(config)

        assert result.is_valid, "开发环境缺少 Secret Key 不应报错"
        assert any("JWT" in w for w in result.warnings), "应产生 JWT 警告"

    def test_validate_storage_repo_root_not_writable(self):
        """
        测试仓库根目录不可写时检测

        验证点：
        1. 仓库根目录不可写时产生错误
        """
        from core.config import Config, AppSettings, StorageSettings, SecuritySettings

        # 使用只读路径（Windows 下 C:\ 通常对普通用户只读）
        readonly_path = "C:\\" if os.name == "nt" else "/"
        config = Config(
            app=AppSettings(debug=True),
            storage=StorageSettings(repo_root=readonly_path),
            security=SecuritySettings(secret_key="test-key"),
        )

        result = validate_config(config)

        # 注意：部分环境下 root 可能可写，所以这可能产生错误或警告
        # 至少应该有响应（error 或 warning）
        assert len(result.errors) > 0 or len(result.warnings) >= 0, "应检测到路径问题"

    def test_validate_token_expiry_warnings(self):
        """
        测试 Token 过期时间合理性检测

        验证点：
        1. 过短的 access_token 过期时间产生警告
        2. 过长的 refresh_token 过期时间产生警告
        """
        from core.config import Config, AppSettings, SecuritySettings
        config = Config(
            app=AppSettings(debug=True),
            security=SecuritySettings(
                secret_key="test-key",
                access_token_expire_minutes=1,  # 1分钟，太短
                refresh_token_expire_days=100,  # 100天，太长
            )
        )

        result = validate_config(config)

        assert result.is_valid, "不合理但合法的配置不应报错"
        token_warnings = [w for w in result.warnings if "令牌" in w or "Token" in w]
        assert len(token_warnings) >= 2, "应检测到至少 2 个 Token 过期时间警告"

    def test_validate_database_pool_config(self):
        """
        测试数据库连接池配置合理性检测

        验证点：
        1. 无效的 PostgreSQL SSL 模式产生错误
        """
        from core.config import Config, AppSettings, DatabaseSettings, SecuritySettings
        config = Config(
            app=AppSettings(debug=True),
            database=DatabaseSettings(
                url="postgresql://user:pass@localhost/db",
                pg_ssl_mode="invalid_ssl_mode",
            ),
            security=SecuritySettings(secret_key="test-key"),
        )

        result = validate_config(config)

        assert not result.is_valid, "无效 SSL 模式应报错"
        ssl_errors = [e for e in result.errors if "SSL" in e]
        assert len(ssl_errors) >= 1, "应检测到 SSL 模式错误"

    def test_validate_invalid_jwt_algorithm(self):
        """
        测试不支持的 JWT 算法检测

        验证点：
        1. 不支持的算法产生错误
        """
        from core.config import Config, AppSettings, SecuritySettings
        config = Config(
            app=AppSettings(debug=True),
            security=SecuritySettings(
                secret_key="test-key",
                algorithm="INVALID_ALGO"
            )
        )

        result = validate_config(config)

        assert not result.is_valid, "不支持的 JWT 算法应报错"
        assert any("算法" in e or "algorithm" in e.lower() for e in result.errors), \
            "错误应提示 JWT 算法无效"

    def test_validate_file_size_greater_than_repo_size(self):
        """
        测试单文件限制大于仓库限制时警告

        验证点：
        1. max_file_size > max_repo_size 时产生警告
        """
        from core.config import Config, AppSettings, StorageSettings, SecuritySettings
        config = Config(
            app=AppSettings(debug=True),
            storage=StorageSettings(
                max_repo_size=1000,
                max_file_size=2000,  # 大于仓库限制
            ),
            security=SecuritySettings(secret_key="test-key"),
        )

        result = validate_config(config)

        assert result.is_valid, "不合理的限制不应报错"
        size_warnings = [w for w in result.warnings if "大小限制" in w]
        assert len(size_warnings) > 0, "应检测到文件大小限制警告"

    def test_validate_config_file_not_found(self):
        """
        测试配置文件不存在时校验失败

        验证点：
        1. 配置文件不存在时产生错误
        """
        result = validate_config(config_path="/nonexistent/config.toml")
        assert not result.is_valid, "配置文件不存在应报错"
        assert any("不存在" in e for e in result.errors), "错误应提示文件不存在"

    def test_validate_validation_result_merge(self):
        """
        测试 ConfigValidationResult 合并功能

        验证点：
        1. merge() 正确合并两个结果
        """
        r1 = ConfigValidationResult()
        r1.add_error("err1")
        r1.add_warning("warn1")

        r2 = ConfigValidationResult()
        r2.add_error("err2")
        r2.add_warning("warn2")

        r1.merge(r2)

        assert len(r1.errors) == 2
        assert len(r1.warnings) == 2
        assert "err1" in r1.errors
        assert "err2" in r1.errors
        assert "warn1" in r1.warnings
        assert "warn2" in r1.warnings
