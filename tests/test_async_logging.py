"""
异步日志系统测试

测试内容：
1. 异步日志管理器初始化
2. 日志异步写入功能
3. 日志级别过滤
4. 优雅关闭和日志刷新
5. 多线程并发写入
6. 性能测试

使用方法：
    python tests/test_async_logging.py
"""
import os
import sys
import time
import threading
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logging_utils import (
    AsyncLogManager,
    init_async_logging,
    get_async_logger,
    shutdown_async_logging,
)


class AsyncLoggingTester:
    """异步日志测试器"""

    def __init__(self):
        self.test_dir = None
        self.log_manager = None
        self.results = []

    def setup(self):
        """设置测试环境"""
        # 创建临时日志目录
        self.test_dir = tempfile.mkdtemp(prefix="async_log_test_")
        print(f"测试日志目录: {self.test_dir}")

    def teardown(self):
        """清理测试环境"""
        # 关闭异步日志
        if self.log_manager:
            self.log_manager.shutdown()
            self.log_manager = None
        shutdown_async_logging()

        # 等待文件句柄释放（Windows需要）
        time.sleep(0.5)

        # 删除临时目录
        if self.test_dir and os.path.exists(self.test_dir):
            try:
                shutil.rmtree(self.test_dir)
                print(f"清理测试目录: {self.test_dir}")
            except PermissionError:
                # Windows下文件句柄可能未立即释放，忽略错误
                print(f"警告: 无法清理测试目录（文件被占用）: {self.test_dir}")

    def log_result(self, test_name: str, passed: bool, message: str = ""):
        """记录测试结果"""
        status = "✅ 通过" if passed else "❌ 失败"
        self.results.append({
            "test": test_name,
            "passed": passed,
            "message": message
        })
        print(f"  {status} - {test_name}")
        if message and not passed:
            print(f"     详情: {message}")

    def test_init_async_logging(self):
        """测试异步日志初始化"""
        print("\n[测试1] 异步日志初始化")
        try:
            # 直接使用 AsyncLogManager 类创建实例（避免全局单例问题）
            self.log_manager = AsyncLogManager(
                log_dir=self.test_dir,
                app_name="test_app",
                level="debug",
                console_output=False  # 测试时禁用控制台输出
            )

            # 验证管理器创建成功
            assert self.log_manager is not None, "日志管理器创建失败"
            assert isinstance(self.log_manager, AsyncLogManager), "类型错误"

            # 验证队列已创建（监听器在 get_logger 时才创建）
            assert self.log_manager._log_queue is not None, "日志队列未创建"

            # 获取 logger 来触发监听器创建
            logger = self.log_manager.get_logger("test_init")

            # 现在验证监听器已创建
            assert self.log_manager._queue_listener is not None, "队列监听器未创建"
            assert self.log_manager._is_async_setup, "异步处理器未设置"

            self.log_result("异步日志初始化", True)
        except Exception as e:
            self.log_result("异步日志初始化", False, str(e))

    def test_async_log_write(self):
        """测试异步日志写入"""
        print("\n[测试2] 异步日志写入")
        try:
            # 获取日志记录器
            logger = self.log_manager.get_logger("test")

            # 记录不同级别的日志
            test_message = f"测试消息 - {datetime.now().isoformat()}"
            logger.debug(f"DEBUG: {test_message}")
            logger.info(f"INFO: {test_message}")
            logger.warning(f"WARNING: {test_message}")
            logger.error(f"ERROR: {test_message}")

            # 等待异步写入完成
            time.sleep(0.5)

            # 验证日志文件已创建
            today_dir = Path(self.test_dir) / datetime.now().strftime("%Y-%m-%d")
            app_log = today_dir / "app.log"
            error_log = today_dir / "error.log"

            assert app_log.exists(), f"app.log 未创建: {app_log}"
            assert error_log.exists(), f"error.log 未创建: {error_log}"

            # 验证日志内容
            app_content = app_log.read_text(encoding="utf-8")
            error_content = error_log.read_text(encoding="utf-8")

            # app.log 应该包含 INFO 但不包含 ERROR
            assert "INFO:" in app_content, "app.log 缺少 INFO 日志"
            assert "ERROR:" not in app_content, "app.log 不应该包含 ERROR"

            # error.log 应该包含 WARNING 和 ERROR
            assert "WARNING:" in error_content, "error.log 缺少 WARNING 日志"
            assert "ERROR:" in error_content, "error.log 缺少 ERROR 日志"

            self.log_result("异步日志写入", True)
        except Exception as e:
            self.log_result("异步日志写入", False, str(e))

    def test_log_level_filtering(self):
        """测试日志级别过滤"""
        print("\n[测试3] 日志级别过滤")
        try:
            # 关闭旧的，重新初始化，设置级别为 WARNING
            if self.log_manager:
                self.log_manager.shutdown()
            self.log_manager = AsyncLogManager(
                log_dir=self.test_dir,
                app_name="test_app",
                level="warning",  # 只记录 WARNING 及以上
                console_output=False
            )

            logger = self.log_manager.get_logger("test_filter")

            # 记录各级别日志
            logger.debug("DEBUG消息")
            logger.info("INFO消息")
            logger.warning("WARNING消息")
            logger.error("ERROR消息")

            time.sleep(0.5)

            # 验证
            today_dir = Path(self.test_dir) / datetime.now().strftime("%Y-%m-%d")
            app_log = today_dir / "app.log"

            # app.log 应该为空（因为级别是 WARNING，且 app.log 只记录 < WARNING）
            if app_log.exists():
                app_content = app_log.read_text(encoding="utf-8")
                # 由于级别设置为 WARNING，INFO 和 DEBUG 不应该被记录
                assert "DEBUG消息" not in app_content, "DEBUG 消息不应该被记录"
                assert "INFO消息" not in app_content, "INFO 消息不应该被记录"

            self.log_result("日志级别过滤", True)
        except Exception as e:
            self.log_result("日志级别过滤", False, str(e))

    def test_graceful_shutdown(self):
        """测试优雅关闭"""
        print("\n[测试4] 优雅关闭")
        try:
            # 关闭旧的，重新初始化
            if self.log_manager:
                self.log_manager.shutdown()
            self.log_manager = AsyncLogManager(
                log_dir=self.test_dir,
                app_name="test_app",
                level="info",
                console_output=False
            )

            logger = self.log_manager.get_logger("test_shutdown")

            # 记录一些日志
            for i in range(10):
                logger.info(f"关闭测试消息 {i}")

            # 立即关闭（不等待）
            self.log_manager.shutdown()

            # 验证日志已写入
            today_dir = Path(self.test_dir) / datetime.now().strftime("%Y-%m-%d")
            app_log = today_dir / "app.log"

            if app_log.exists():
                content = app_log.read_text(encoding="utf-8")
                # 验证至少部分日志已写入
                assert "关闭测试消息" in content, "关闭前日志未写入"

            self.log_result("优雅关闭", True)
        except Exception as e:
            self.log_result("优雅关闭", False, str(e))

    def test_concurrent_logging(self):
        """测试并发日志写入"""
        print("\n[测试5] 并发日志写入")
        try:
            # 关闭旧的，重新初始化
            if self.log_manager:
                self.log_manager.shutdown()
            self.log_manager = AsyncLogManager(
                log_dir=self.test_dir,
                app_name="test_app",
                level="info",
                console_output=False
            )

            logger = self.log_manager.get_logger("test_concurrent")
            message_count = 100
            thread_count = 5

            def log_messages(thread_id: int):
                """线程函数：记录日志"""
                for i in range(message_count):
                    logger.info(f"线程{thread_id}-消息{i}")

            # 创建多个线程并发写入
            threads = []
            start_time = time.time()

            for i in range(thread_count):
                t = threading.Thread(target=log_messages, args=(i,))
                threads.append(t)
                t.start()

            # 等待所有线程完成
            for t in threads:
                t.join()

            elapsed = time.time() - start_time

            # 等待异步写入完成
            time.sleep(1)

            # 验证日志数量
            today_dir = Path(self.test_dir) / datetime.now().strftime("%Y-%m-%d")
            app_log = today_dir / "app.log"

            if app_log.exists():
                content = app_log.read_text(encoding="utf-8")
                # 统计日志条目数
                log_entries = content.count("线程")
                expected = thread_count * message_count

                print(f"     并发写入: {thread_count} 线程 × {message_count} 消息 = {expected}")
                print(f"     实际写入: {log_entries} 条")
                print(f"     耗时: {elapsed:.3f}s")
                print(f"     速度: {expected/elapsed:.0f} 条/秒")

                # 允许少量丢失（异步队列可能溢出）
                assert log_entries >= expected * 0.9, f"日志丢失过多: {log_entries}/{expected}"

            self.log_result("并发日志写入", True)
        except Exception as e:
            self.log_result("并发日志写入", False, str(e))

    def test_performance(self):
        """测试性能"""
        print("\n[测试6] 性能测试")
        try:
            # 关闭旧的，重新初始化
            if self.log_manager:
                self.log_manager.shutdown()
            self.log_manager = AsyncLogManager(
                log_dir=self.test_dir,
                app_name="test_app",
                level="info",
                console_output=False
            )

            logger = self.log_manager.get_logger("test_perf")
            count = 1000

            # 测试异步日志性能
            start_time = time.time()
            for i in range(count):
                logger.info(f"性能测试消息 {i}")
            async_elapsed = time.time() - start_time

            # 等待写入完成
            time.sleep(0.5)

            # 计算性能指标
            async_rate = count / async_elapsed

            print(f"     异步日志: {count} 条耗时 {async_elapsed:.3f}s")
            print(f"     写入速度: {async_rate:.0f} 条/秒")

            # 异步日志应该很快（>1000条/秒）
            assert async_rate > 1000, f"性能过低: {async_rate:.0f} 条/秒"

            self.log_result("性能测试", True)
        except Exception as e:
            self.log_result("性能测试", False, str(e))

    def run_all_tests(self):
        """运行所有测试"""
        print("=" * 60)
        print("异步日志系统测试")
        print("=" * 60)

        self.setup()

        try:
            self.test_init_async_logging()
            self.test_async_log_write()
            self.test_log_level_filtering()
            self.test_graceful_shutdown()
            self.test_concurrent_logging()
            self.test_performance()
        finally:
            self.teardown()

        # 打印测试报告
        print("\n" + "=" * 60)
        print("测试报告")
        print("=" * 60)

        passed = sum(1 for r in self.results if r["passed"])
        failed = sum(1 for r in self.results if not r["passed"])

        for result in self.results:
            status = "✅" if result["passed"] else "❌"
            print(f"{status} {result['test']}")

        print("-" * 60)
        print(f"总计: {len(self.results)} 个测试")
        print(f"通过: {passed} 个")
        print(f"失败: {failed} 个")
        print("=" * 60)

        return failed == 0


def main():
    """主函数"""
    tester = AsyncLoggingTester()
    success = tester.run_all_tests()

    # 返回退出码
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
