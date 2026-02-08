"""
测试仓库 API 响应包含物理仓库信息

验证所有仓库相关 API 都返回 physical 字段
"""
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from models import SessionLocal, Repository
from services.repository_service import (
    get_repositories,
    get_repository_by_id,
    get_repositories_by_user,
    get_public_repositories,
    create_repository,
    update_repository,
    _build_repo_response
)


def check_repo_response_format(repo_data: dict, test_name: str):
    """检查仓库响应格式是否包含 physical 字段"""
    assert "id" in repo_data, f"{test_name}: 缺少 id 字段"
    assert "name" in repo_data, f"{test_name}: 缺少 name 字段"
    assert "path" in repo_data, f"{test_name}: 缺少 path 字段"
    assert "physical" in repo_data, f"{test_name}: 缺少 physical 字段"
    assert "path" in repo_data["physical"], f"{test_name}: physical 缺少 path 字段"
    assert "exists" in repo_data["physical"], f"{test_name}: physical 缺少 exists 字段"
    assert isinstance(repo_data["physical"]["exists"], bool), f"{test_name}: physical.exists 应该是布尔值"
    print(f"  ✅ {test_name} 格式正确")


async def test_build_repo_response():
    """测试 _build_repo_response 辅助函数"""
    print("\n=== 测试 _build_repo_response ===")

    db = SessionLocal()
    try:
        # 获取第一个仓库进行测试
        repo = db.query(Repository).first()
        if repo is None:
            print("  ⚠️ 数据库中没有仓库，跳过测试")
            return

        response = _build_repo_response(repo)
        check_repo_response_format(response, "_build_repo_response")
        print(f"  物理路径: {response['physical']['path']}")
        print(f"  物理存在: {response['physical']['exists']}")

    finally:
        db.close()


async def test_get_repositories():
    """测试获取所有仓库 API"""
    print("\n=== 测试 get_repositories ===")

    db = SessionLocal()
    try:
        repos = await get_repositories(db)
        print(f"  获取到 {len(repos)} 个仓库")

        for repo in repos:
            check_repo_response_format(repo, f"仓库 {repo.get('name', 'unknown')}")

    finally:
        db.close()


async def test_get_repository_by_id():
    """测试根据 ID 获取仓库 API"""
    print("\n=== 测试 get_repository_by_id ===")

    db = SessionLocal()
    try:
        # 获取第一个仓库的 ID
        first_repo = db.query(Repository).first()
        if first_repo is None:
            print("  ⚠️ 数据库中没有仓库，跳过测试")
            return

        repo = await get_repository_by_id(first_repo.id, db)
        check_repo_response_format(repo, f"仓库 ID {first_repo.id}")
        print(f"  物理路径: {repo['physical']['path']}")
        print(f"  物理存在: {repo['physical']['exists']}")

    finally:
        db.close()


async def test_get_public_repositories():
    """测试获取公开仓库 API"""
    print("\n=== 测试 get_public_repositories ===")

    db = SessionLocal()
    try:
        repos = await get_public_repositories(db)
        print(f"  获取到 {len(repos)} 个公开仓库")

        for repo in repos:
            check_repo_response_format(repo, f"公开仓库 {repo.get('name', 'unknown')}")

    finally:
        db.close()


async def main():
    """运行所有测试"""
    print("=" * 60)
    print("测试仓库 API 响应包含物理仓库信息")
    print("=" * 60)

    try:
        await test_build_repo_response()
        await test_get_repositories()
        await test_get_repository_by_id()
        await test_get_public_repositories()

        print("\n" + "=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)
        print("\nAPI 响应现在包含 physical 字段:")
        print("  - physical.path: 物理仓库路径")
        print("  - physical.exists: 物理仓库是否存在")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
