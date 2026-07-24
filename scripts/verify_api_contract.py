"""API 契约一致性检查脚本

用法：
    python scripts/verify_api_contract.py

说明：
    该脚本加载 FastAPI 应用实例，读取真实注册的路由表，再与前端 API 调用文件
    中的路径、方法进行对比，输出可能存在不一致的接口。
    需要 config.toml 存在，但不启动服务器、不依赖数据库。
"""
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_API_DIR = PROJECT_ROOT / "client" / "web" / "src" / "api"


def collect_backend_routes(app) -> set[tuple[str, str]]:
    """从 FastAPI 应用中提取所有已注册的 HTTP 路由"""
    routes = set()
    for route in app.routes:
        if hasattr(route, "methods") and hasattr(route, "path"):
            for method in route.methods:
                if method == "HEAD":
                    continue
                routes.add((method.upper(), route.path))
    return routes


def collect_frontend_apis() -> list[dict]:
    """扫描前端 api/*.ts 文件，提取 apiRequest 调用"""
    apis = []
    if not FRONTEND_API_DIR.exists():
        print(f"[警告] 前端 API 目录不存在: {FRONTEND_API_DIR}")
        return apis

    api_request_pattern = re.compile(
        r"apiRequest<[^>]+>\(\s*['\"`](?P<path>/[^'\"`]+)['\"`]\s*(?:,\s*\{[\s\S]*?method:\s*['\"](?P<method>[A-Z]+)['\"][\s\S]*?\})?",
        re.MULTILINE,
    )

    for file_path in FRONTEND_API_DIR.glob("*.ts"):
        content = file_path.read_text(encoding="utf-8")
        for match in api_request_pattern.finditer(content):
            path = match.group("path")
            method = (match.group("method") or "GET").upper()
            apis.append({"file": file_path.name, "method": method, "path": path})
    return apis


def _camel_to_snake(name: str) -> str:
    """将 camelCase 转换为 snake_case"""
    name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    return name.lower()


def normalize_frontend_path(path: str) -> str:
    """将前端路径统一为后端 FastAPI 路由风格，便于对比"""
    # 把 ${repoId} 等转换为 {repoId}
    path = re.sub(r"\$\{(\w+?)\}", r"{\1}", path)
    # 移除查询参数（后端路由表不含查询参数）
    path = path.split("?")[0]
    # 移除 ${qs}、{qs} 等查询字符串占位符
    path = re.sub(r"\$?\{\s*qs\s*\}", "", path)
    # 将剩余的 JS 表达式片段（如 ${encodeURIComponent(tagName)}）替换为 {id}
    path = re.sub(r"\$\{[^}]+\}", "{id}", path)
    # 将 camelCase 变量名转换为 snake_case
    def convert_var(match: re.Match) -> str:
        var_name = match.group(1)
        return "{" + _camel_to_snake(var_name) + "}"

    path = re.sub(r"\{([a-zA-Z0-9_]+)\}", convert_var, path)
    return path


def main() -> int:
    sys.path.insert(0, str(PROJECT_ROOT))
    try:
        from app import app
    except Exception as exc:
        print(f"[错误] 无法加载 FastAPI 应用: {exc}")
        return 1

    backend_routes = collect_backend_routes(app)
    frontend_apis = collect_frontend_apis()

    print(f"后端路由数量: {len(backend_routes)}")
    print(f"前端 API 调用数量: {len(frontend_apis)}")
    print()

    if not frontend_apis:
        print("[警告] 未扫描到前端 API 调用")
        return 0

    # 为忽略动态参数命名差异，再生成一份把参数占位符统一为 {} 的骨架路由表
    backend_skeletons = {(method, re.sub(r"\{[^}]+\}", "{}", path)) for method, path in backend_routes}

    issues = []
    for api in frontend_apis:
        normalized = normalize_frontend_path(api["path"])
        if (api["method"], normalized) not in backend_routes:
            skeleton = re.sub(r"\{[^}]+\}", "{}", normalized)
            if (api["method"], skeleton) not in backend_skeletons:
                issues.append(api)

    if not issues:
        print("✅ 未发现明显的前后端路径/方法不一致")
        return 0

    print("⚠️  发现以下前端 API 调用在后端路由表中未找到精确匹配：")
    print("-" * 80)
    for api in issues:
        print(f"文件: {api['file']}")
        print(f"方法: {api['method']}")
        print(f"路径: {api['path']}")
        print(f"归一化: {normalize_frontend_path(api['path'])}")
        print("-" * 80)

    print()
    print(
        "提示：上述不匹配通常是路径错误或 HTTP 方法错误，请结合业务逻辑人工复核。"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
