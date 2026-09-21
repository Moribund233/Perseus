"""物理仓库存在状态缓存 L2（Redis）与失效（规划 R5-2）"""
import uuid
from types import SimpleNamespace

import pytest

from services import repository_service


class _FakeRedis:
    def __init__(self):
        self.store = {}

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value, ex=None):
        self.store[key] = value

    async def delete(self, key):
        self.store.pop(key, None)


@pytest.fixture(autouse=True)
def _clear_local():
    repository_service._repo_exists_cache.clear()
    yield
    repository_service._repo_exists_cache.clear()


def _repo():
    return SimpleNamespace(id=uuid.uuid4(), path="owner/repo")


def _patch(monkeypatch, fake_redis, disk_result=True, counter=None):
    async def _get_redis():
        return fake_redis

    async def _repo_exists(path):
        if counter is not None:
            counter["n"] += 1
        return disk_result

    monkeypatch.setattr(repository_service, "get_redis", _get_redis)
    monkeypatch.setattr(repository_service, "repo_exists_async", _repo_exists)
    monkeypatch.setattr(repository_service, "get_repository_storage_path", lambda p: f"/x/{p}")


async def test_disk_then_redis_l2(monkeypatch):
    fake = _FakeRedis()
    counter = {"n": 0}
    _patch(monkeypatch, fake, disk_result=True, counter=counter)
    repo = _repo()

    assert await repository_service._check_physical_repo_exists_async(repo) is True
    assert counter["n"] == 1

    # 清 L1，命中 Redis L2，不再触盘
    repository_service._repo_exists_cache.clear()
    assert await repository_service._check_physical_repo_exists_async(repo) is True
    assert counter["n"] == 1


async def test_l2_false_value(monkeypatch):
    fake = _FakeRedis()
    _patch(monkeypatch, fake, disk_result=False)
    repo = _repo()

    assert await repository_service._check_physical_repo_exists_async(repo) is False
    repository_service._repo_exists_cache.clear()
    assert await repository_service._check_physical_repo_exists_async(repo) is False


async def test_no_redis_falls_back_to_disk(monkeypatch):
    async def _none():
        return None

    counter = {"n": 0}

    async def _repo_exists(path):
        counter["n"] += 1
        return True

    monkeypatch.setattr(repository_service, "get_redis", _none)
    monkeypatch.setattr(repository_service, "repo_exists_async", _repo_exists)
    monkeypatch.setattr(repository_service, "get_repository_storage_path", lambda p: f"/x/{p}")
    repo = _repo()

    assert await repository_service._check_physical_repo_exists_async(repo) is True
    repository_service._repo_exists_cache.clear()
    assert await repository_service._check_physical_repo_exists_async(repo) is True
    assert counter["n"] == 2  # 无 L2，仍触盘


async def test_invalidate_clears_l1_and_l2(monkeypatch):
    fake = _FakeRedis()
    _patch(monkeypatch, fake)
    repo = _repo()
    await repository_service._check_physical_repo_exists_async(repo)
    assert repository_service._repo_exists_key(repo.id) in fake.store

    await repository_service._invalidate_repo_exists_cache(repo.id)

    assert repo.id not in repository_service._repo_exists_cache
    assert repository_service._repo_exists_key(repo.id) not in fake.store
