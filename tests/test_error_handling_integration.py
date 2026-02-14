"""
错误处理集成测试脚本

测试异常处理机制的完整流程，包括：
1. 各种自定义异常的处理
2. Python 内置异常的处理
3. 调试模式与生产模式的差异
4. 管理员与普通用户的权限差异

使用方法：
1. 确保服务器运行在调试模式 (debug=True)
2. 运行测试: python tests/test_error_handling_integration.py
3. 检查日志输出和响应结果
"""
import requests
import json
import sys
from typing import Dict, Any

# 测试配置
BASE_URL = "http://localhost:8000"
TEST_ENDPOINTS = [
    # 自定义异常测试
    {"name": "验证异常", "path": "/api/test/errors/validation", "expected_status": 400},
    {"name": "认证异常", "path": "/api/test/errors/authentication", "expected_status": 401},
    {"name": "授权异常", "path": "/api/test/errors/authorization", "expected_status": 403},
    {"name": "资源不存在", "path": "/api/test/errors/not-found", "expected_status": 404},
    {"name": "资源冲突", "path": "/api/test/errors/conflict", "expected_status": 409},
    {"name": "数据库异常", "path": "/api/test/errors/database", "expected_status": 500},

    # Python 内置异常测试
    {"name": "内部错误(除零)", "path": "/api/test/errors/internal", "expected_status": 500},
    {"name": "键错误", "path": "/api/test/errors/key-error", "expected_status": 500},
    {"name": "类型错误", "path": "/api/test/errors/type-error", "expected_status": 500},
    {"name": "值错误", "path": "/api/test/errors/value-error", "expected_status": 500},
    {"name": "属性错误", "path": "/api/test/errors/attribute-error", "expected_status": 500},
    {"name": "嵌套错误", "path": "/api/test/errors/nested-error", "expected_status": 500},

    # HTTP 异常测试
    {"name": "HTTP异常", "path": "/api/test/errors/http-exception", "expected_status": 418},
]


def print_separator(title: str = ""):
    """打印分隔线"""
    if title:
        print(f"\n{'=' * 60}")
        print(f" {title}")
        print(f"{'=' * 60}")
    else:
        print(f"\n{'=' * 60}")


def print_response(response: requests.Response, name: str):
    """打印响应信息"""
    print(f"\n📌 测试: {name}")
    print(f"   状态码: {response.status_code}")
    print(f"   响应头: {dict(response.headers)}")

    try:
        data = response.json()
        print(f"   响应体:")
        print(json.dumps(data, indent=4, ensure_ascii=False))

        # 检查是否包含堆栈跟踪
        if "traceback" in data and data["traceback"]:
            print(f"   ⚠️  包含堆栈跟踪: 是")
        else:
            print(f"   ℹ️  包含堆栈跟踪: 否")

        # 检查错误详情
        if "error" in data:
            error = data["error"]
            print(f"   错误类型: {error.get('type', 'N/A')}")
            print(f"   错误消息: {error.get('message', 'N/A')}")

    except json.JSONDecodeError:
        print(f"   响应体 (非JSON): {response.text[:200]}")


def test_error_endpoint(endpoint: Dict[str, Any]) -> bool:
    """测试单个错误端点"""
    url = f"{BASE_URL}{endpoint['path']}"
    name = endpoint['name']
    expected_status = endpoint['expected_status']

    try:
        response = requests.get(url, timeout=10)
        print_response(response, name)

        if response.status_code == expected_status:
            print(f"   ✅ 状态码匹配 ({expected_status})")
            return True
        else:
            print(f"   ❌ 状态码不匹配 (期望 {expected_status}, 实际 {response.status_code})")
            return False

    except requests.exceptions.ConnectionError:
        print(f"\n📌 测试: {name}")
        print(f"   ❌ 连接失败: 无法连接到服务器 {BASE_URL}")
        print(f"   请确保服务器已启动: python app.py")
        return False
    except requests.exceptions.Timeout:
        print(f"\n📌 测试: {name}")
        print(f"   ❌ 请求超时")
        return False
    except Exception as e:
        print(f"\n📌 测试: {name}")
        print(f"   ❌ 请求异常: {e}")
        return False


def test_error_info_endpoint():
    """测试错误信息查询端点"""
    print_separator("测试错误信息查询端点")

    # 测试无认证访问
    print("\n📌 测试: 无认证访问错误信息")
    url = f"{BASE_URL}/api/errors/info/500?message=测试错误&error_type=TestError&details=详细错误信息"
    response = requests.get(url)
    print_response(response, "无认证访问")

    # 检查是否隐藏了详细信息
    try:
        data = response.json()
        if data.get("details") is None and data.get("traceback") is None:
            print("   ✅ 未认证用户正确隐藏了详细信息")
        else:
            print("   ⚠️  未认证用户可能看到了详细信息")
    except:
        pass


def test_stack_trace_in_logs():
    """提示用户检查日志"""
    print_separator("日志检查提示")
    print("""
请检查以下日志文件，确认是否包含堆栈跟踪信息：

1. 控制台输出 - 应该看到简化格式的错误信息
2. logs/YYYY-MM-DD/app.log - 应该包含完整的堆栈跟踪
3. logs/YYYY-MM-DD/error.log - 应该只包含 WARNING 及以上级别的错误

在调试模式下，你应该能在 app.log 中看到类似以下的内容：

2024-01-15 10:30:45 - langit.exception - ERROR - Exception: 测试错误
Traceback (most recent call last):
  File "...", line XX, in ...
    ...
  File "...", line XX, in ...
    ...
""")


def main():
    """主测试函数"""
    print_separator("异常处理机制集成测试")
    print(f"测试服务器: {BASE_URL}")
    print(f"测试端点数量: {len(TEST_ENDPOINTS)}")

    # 测试所有端点
    print_separator("测试自定义异常和内置异常")
    results = []
    for endpoint in TEST_ENDPOINTS:
        success = test_error_endpoint(endpoint)
        results.append((endpoint['name'], success))

    # 测试错误信息查询端点
    test_error_info_endpoint()

    # 日志检查提示
    test_stack_trace_in_logs()

    # 汇总结果
    print_separator("测试结果汇总")
    passed = sum(1 for _, success in results if success)
    total = len(results)
    print(f"通过: {passed}/{total}")

    if passed < total:
        print("\n失败的测试:")
        for name, success in results:
            if not success:
                print(f"  ❌ {name}")

    print_separator()

    # 返回退出码
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
