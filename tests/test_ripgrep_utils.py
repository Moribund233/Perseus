"""Ripgrep 工具测试"""
import pytest
from utils.ripgrep_utils import is_available, search_code


class TestRipgrepAvailability:
    def test_is_available_returns_bool(self):
        result = is_available()
        assert isinstance(result, bool)

    def test_is_available_on_system_with_ripgrep(self):
        # This test assumes ripgrep is installed in test environment
        # If not installed, it should return False gracefully
        result = is_available()
        # Just verify it doesn't raise
        assert result in (True, False)


class TestRipgrepSearch:
    def test_search_code_returns_list(self):
        # Test with a known directory
        import tempfile
        import os
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test file
            test_file = os.path.join(tmpdir, "test.py")
            with open(test_file, "w") as f:
                f.write("def hello():\n    pass\n")
            
            results = search_code(tmpdir, "hello")
            assert isinstance(results, list)

    def test_search_code_with_matches(self):
        import tempfile
        import os
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test.py")
            with open(test_file, "w") as f:
                f.write("def hello():\n    pass\n")
            
            results = search_code(tmpdir, "hello")
            assert len(results) > 0
            assert results[0]["file"] == "test.py"
            assert results[0]["line"] == 1
            assert "hello" in results[0]["content"]

    def test_search_code_no_matches(self):
        import tempfile
        import os
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test.py")
            with open(test_file, "w") as f:
                f.write("def hello():\n    pass\n")
            
            results = search_code(tmpdir, "nonexistent_function")
            assert results == []

    def test_search_code_with_path_filter(self):
        import tempfile
        import os
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create files in different directories
            os.makedirs(os.path.join(tmpdir, "src"))
            os.makedirs(os.path.join(tmpdir, "tests"))
            
            with open(os.path.join(tmpdir, "src", "main.py"), "w") as f:
                f.write("def hello():\n    pass\n")
            with open(os.path.join(tmpdir, "tests", "test_main.py"), "w") as f:
                f.write("def test_hello():\n    pass\n")
            
            results = search_code(tmpdir, "hello", path="src")
            assert len(results) == 1
            assert "src" in results[0]["file"]