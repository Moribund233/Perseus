"""LFS 指针文件工具测试"""
import pytest
from utils.lfs_utils import parse_pointer, create_pointer, is_lfs_pointer, LFSPointer


class TestParsePointer:
    def test_parse_valid_pointer(self):
        content = "version https://git-lfs.github.com/spec/v1\noid sha256:4d7a214614ab2935c943f9e0ff69d22eadbb8f32b1258daaa5e2ca24d17e2393\nsize 1234567\n"
        result = parse_pointer(content)
        assert isinstance(result, LFSPointer)
        assert result.version == "https://git-lfs.github.com/spec/v1"
        assert result.oid == "sha256:4d7a214614ab2935c943f9e0ff69d22eadbb8f32b1258daaa5e2ca24d17e2393"
        assert result.size == 1234567

    def test_parse_pointer_with_custom_headers(self):
        content = "version https://git-lfs.github.com/spec/v1\noid sha256:abc123\nsize 100\nx-custom: value\n"
        result = parse_pointer(content)
        assert result.oid == "sha256:abc123"
        assert result.size == 100

    def test_parse_pointer_invalid_version(self):
        content = "version https://invalid.com/spec/v1\noid sha256:abc123\nsize 100\n"
        with pytest.raises(ValueError) as exc:
            parse_pointer(content)
        assert "Invalid LFS pointer" in str(exc.value)

    def test_parse_pointer_missing_oid(self):
        content = "version https://git-lfs.github.com/spec/v1\nsize 100\n"
        with pytest.raises(ValueError) as exc:
            parse_pointer(content)
        assert "Missing required field" in str(exc.value)

    def test_parse_pointer_missing_size(self):
        content = "version https://git-lfs.github.com/spec/v1\noid sha256:abc123\n"
        with pytest.raises(ValueError) as exc:
            parse_pointer(content)
        assert "Missing required field" in str(exc.value)

    def test_parse_pointer_invalid_size(self):
        content = "version https://git-lfs.github.com/spec/v1\noid sha256:abc123\nsize not_a_number\n"
        with pytest.raises(ValueError) as exc:
            parse_pointer(content)
        assert "Invalid size" in str(exc.value)


class TestCreatePointer:
    def test_create_pointer(self):
        oid = "sha256:4d7a214614ab2935c943f9e0ff69d22eadbb8f32b1258daaa5e2ca24d17e2393"
        size = 1234567
        result = create_pointer(oid, size)
        assert "version https://git-lfs.github.com/spec/v1" in result
        assert f"oid {oid}" in result
        assert f"size {size}" in result

    def test_create_pointer_format(self):
        oid = "sha256:abc123"
        size = 100
        result = create_pointer(oid, size)
        lines = result.strip().split("\n")
        assert len(lines) == 3
        assert lines[0] == "version https://git-lfs.github.com/spec/v1"
        assert lines[1] == f"oid {oid}"
        assert lines[2] == f"size {size}"


class TestIsLFSPointer:
    def test_is_lfs_pointer_true(self):
        content = "version https://git-lfs.github.com/spec/v1\noid sha256:abc123\nsize 100\n"
        assert is_lfs_pointer(content) is True

    def test_is_lfs_pointer_false(self):
        content = "This is a regular file content"
        assert is_lfs_pointer(content) is False

    def test_is_lfs_pointer_empty(self):
        assert is_lfs_pointer("") is False

    def test_is_lfs_pointer_partial(self):
        content = "version https://git-lfs.github.com/spec/v1\n"
        assert is_lfs_pointer(content) is False