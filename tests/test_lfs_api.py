"""LFS API 端点测试"""
import os
import tempfile
import shutil
import pytest
from fastapi.testclient import TestClient

from models.repository import Repository
from utils.git_utils import init_bare_repo, get_repository_storage_path
from tests.test_helpers import create_test_repo as _create_test_repo


@pytest.fixture(autouse=True, scope="session")
def _setup_lfs_temp_path():
    """设置临时 LFS 存储路径"""
    old_value = os.environ.get("PERSEUS_LFS_LOCAL_PATH")
    tmpdir = tempfile.mkdtemp(prefix="perseus_lfs_test_")
    os.environ["PERSEUS_LFS_LOCAL_PATH"] = tmpdir
    yield
    shutil.rmtree(tmpdir, ignore_errors=True)
    if old_value is not None:
        os.environ["PERSEUS_LFS_LOCAL_PATH"] = old_value
    else:
        os.environ.pop("PERSEUS_LFS_LOCAL_PATH", None)


def create_test_repo(db, name: str = "lfs-test-repo") -> Repository:
    """创建测试仓库（含物理 Git 仓库初始化）"""
    repo = _create_test_repo(db, name=name)
    physical_path = get_repository_storage_path(repo.path)
    init_bare_repo(physical_path)
    return repo


class TestLFSAPI:
    def test_batch_upload_request(self, test_client: TestClient, auth_headers: dict, db):
        repo = create_test_repo(db, name="lfs-test-repo")

        response = test_client.post(
            f"/api/v1/repositories/{repo.id}/lfs/objects/batch",
            json={
                "operation": "upload",
                "transfers": ["basic"],
                "ref": {"name": "main"},
                "objects": [
                    {"oid": "sha256:abc123", "size": 1024}
                ],
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "objects" in data
        assert len(data["objects"]) == 1
        assert "actions" in data["objects"][0]

    def test_batch_download_request(self, test_client: TestClient, auth_headers: dict, db):
        repo = create_test_repo(db, name="lfs-download-repo")

        response = test_client.post(
            f"/api/v1/repositories/{repo.id}/lfs/objects/batch",
            json={
                "operation": "download",
                "objects": [
                    {"oid": "sha256:abc123"}
                ],
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["objects"][0]["actions"]["download"]["href"]

    def test_upload_object(self, test_client: TestClient, auth_headers: dict, db):
        repo = create_test_repo(db, name="lfs-upload-repo")

        oid = "sha256:4d7a214614ab2935c943f9e0ff69d22eadbb8f32b1258daaa5e2ca24d17e2393"
        response = test_client.put(
            f"/api/v1/repositories/{repo.id}/lfs/objects/{oid}",
            content=b"Hello, LFS!",
            headers={**auth_headers, "Content-Type": "application/octet-stream"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["oid"] == oid

    def test_download_object(self, test_client: TestClient, auth_headers: dict, db):
        repo = create_test_repo(db, name="lfs-dl-repo")

        oid = "sha256:download_test"
        # 先上传
        test_client.put(
            f"/api/v1/repositories/{repo.id}/lfs/objects/{oid}",
            content=b"Download me",
            headers={**auth_headers, "Content-Type": "application/octet-stream"},
        )

        response = test_client.get(
            f"/api/v1/repositories/{repo.id}/lfs/objects/{oid}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.content == b"Download me"

    def test_upload_requires_auth(self, test_client: TestClient, db):
        repo = create_test_repo(db, name="lfs-noauth-repo")

        oid = "sha256:noauth_test"
        response = test_client.put(
            f"/api/v1/repositories/{repo.id}/lfs/objects/{oid}",
            content=b"data",
            headers={"Content-Type": "application/octet-stream"},
        )
        assert response.status_code == 401

    def test_delete_object(self, test_client: TestClient, auth_headers: dict, db):
        repo = create_test_repo(db, name="lfs-delete-repo")

        oid = "sha256:delete_test"
        # 先上传
        test_client.put(
            f"/api/v1/repositories/{repo.id}/lfs/objects/{oid}",
            content=b"Delete me",
            headers={**auth_headers, "Content-Type": "application/octet-stream"},
        )

        response = test_client.delete(
            f"/api/v1/repositories/{repo.id}/lfs/objects/{oid}",
            headers=auth_headers,
        )
        assert response.status_code == 204
