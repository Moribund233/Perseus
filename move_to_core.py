"""
批量修改Python文件引用路径脚本

功能：
1. 将指定的Python文件移动到core目录
2. 自动修改所有相关文件的import引用路径

使用方法:
    python move_to_core.py [--execute]

参数:
    --execute: 实际执行移动和修改操作（默认只预览）
"""
import os
import re
import shutil
import argparse
from pathlib import Path
from typing import List, Tuple, Dict


# 配置：需要移动到core目录的文件
FILES_TO_MOVE = [
    "init.py",
    "config.py",
    "lifespan.py",
    "exception.py",
    "gunicorn_worker.py",
    "gunicorn.conf.py",
]

# 目标目录
TARGET_DIR = "core"

# 项目根目录
PROJECT_ROOT = Path(__file__).parent


def get_all_python_files() -> List[Path]:
    """
    获取项目中所有的Python文件（排除特定目录）

    Returns:
        List[Path]: Python文件路径列表
    """
    python_files = []
    exclude_dirs = {
        "__pycache__",
        ".git",
        ".venv",
        "venv",
        "node_modules",
        ".pytest_cache",
        TARGET_DIR,  # 排除目标目录本身
    }

    for root, dirs, files in os.walk(PROJECT_ROOT):
        # 排除特定目录
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for file in files:
            if file.endswith(".py"):
                python_files.append(Path(root) / file)

    return python_files


def build_import_patterns(filename: str) -> List[Tuple[str, str, str]]:
    """
    构建import匹配模式

    Args:
        filename: 文件名（不含路径）

    Returns:
        List[Tuple[str, str, str]]: (模式, 替换模板, 描述)
    """
    module_name = filename.replace(".py", "").replace(".", "_")

    patterns = []

    # from xxx import yyy -> from core.xxx import yyy
    patterns.append((
        rf"from\s+{module_name}\s+import",
        f"from core.{module_name} import",
        f"from {module_name} import"
    ))

    # import xxx -> import core.xxx (作为模块导入的情况)
    patterns.append((
        rf"^import\s+{module_name}$",
        f"import core.{module_name}",
        f"import {module_name}"
    ))

    # import xxx as -> import core.xxx as
    patterns.append((
        rf"import\s+{module_name}\s+as",
        f"import core.{module_name} as",
        f"import {module_name} as"
    ))

    # from xxx.yyy import (子模块导入)
    if "." in filename.replace(".py", ""):
        # gunicorn.conf 特殊处理
        parts = filename.replace(".py", "").split(".")
        original = ".".join(parts)
        patterns.append((
            rf"from\s+{original}\s+import",
            f"from core.{original} import",
            f"from {original} import"
        ))
        patterns.append((
            rf"import\s+{original}",
            f"import core.{original}",
            f"import {original}"
        ))

    return patterns


def process_file(file_path: Path, patterns_map: Dict[str, List[Tuple[str, str, str]]]) -> Tuple[bool, List[str]]:
    """
    处理单个文件，修改import语句

    Args:
        file_path: 文件路径
        patterns_map: 文件名到匹配模式的映射

    Returns:
        Tuple[bool, List[str]]: (是否修改, 修改记录)
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            lines = content.split("\n")
    except Exception as e:
        return False, [f"读取文件失败: {e}"]

    modified = False
    changes = []
    new_lines = []

    for line_num, line in enumerate(lines, 1):
        original_line = line
        new_line = line

        for filename, patterns in patterns_map.items():
            for pattern, replacement, desc in patterns:
                # 使用正则表达式匹配
                if re.search(pattern, line):
                    new_line = re.sub(pattern, replacement, line)
                    if new_line != original_line:
                        changes.append(
                            f"  第{line_num}行: {original_line.strip()} -> {new_line.strip()}"
                        )
                        modified = True
                        break

        new_lines.append(new_line)

    if modified:
        return True, changes

    return False, []


def ensure_core_init() -> None:
    """确保core目录存在且有__init__.py文件"""
    core_dir = PROJECT_ROOT / TARGET_DIR
    core_dir.mkdir(exist_ok=True)

    init_file = core_dir / "__init__.py"
    if not init_file.exists():
        init_content = '''"""
核心模块包

包含应用核心配置和基础设施组件
"""
'''
        with open(init_file, "w", encoding="utf-8") as f:
            f.write(init_content)
        print(f"创建: {init_file}")


def move_files() -> List[Tuple[str, str]]:
    """
    移动文件到core目录

    Returns:
        List[Tuple[str, str]]: (原路径, 新路径)列表
    """
    moved_files = []
    core_dir = PROJECT_ROOT / TARGET_DIR

    for filename in FILES_TO_MOVE:
        src = PROJECT_ROOT / filename
        dst = core_dir / filename

        if src.exists():
            if dst.exists():
                print(f"警告: 目标文件已存在，跳过: {dst}")
                continue
            shutil.move(str(src), str(dst))
            moved_files.append((str(src), str(dst)))
            print(f"移动: {src} -> {dst}")
        else:
            print(f"警告: 源文件不存在: {src}")

    return moved_files


def main():
    parser = argparse.ArgumentParser(description="批量修改Python文件引用路径")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="实际执行移动和修改操作（默认只预览）"
    )
    args = parser.parse_args()

    print("=" * 70)
    print("Python文件引用路径批量修改工具")
    print("=" * 70)
    print(f"\n计划移动的文件:")
    for f in FILES_TO_MOVE:
        print(f"  - {f}")
    print(f"\n目标目录: {TARGET_DIR}/")
    print(f"\n模式: {'执行模式' if args.execute else '预览模式'}")
    print("=" * 70)

    # 构建匹配模式
    patterns_map = {}
    for filename in FILES_TO_MOVE:
        patterns_map[filename] = build_import_patterns(filename)

    # 获取所有Python文件
    python_files = get_all_python_files()
    print(f"\n扫描到 {len(python_files)} 个Python文件")

    # 处理每个文件
    files_to_modify = []
    for file_path in python_files:
        modified, changes = process_file(file_path, patterns_map)
        if modified:
            files_to_modify.append((file_path, changes))

    if not files_to_modify:
        print("\n没有找到需要修改的文件")
        return

    print(f"\n找到 {len(files_to_modify)} 个文件需要修改:")
    for file_path, changes in files_to_modify:
        print(f"\n{file_path}")
        for change in changes:
            print(change)

    if not args.execute:
        print("\n" + "=" * 70)
        print("这是预览模式，没有实际修改文件")
        print("使用 --execute 参数执行实际修改")
        print("=" * 70)
        return

    # 执行模式
    print("\n" + "=" * 70)
    print("开始执行修改...")
    print("=" * 70)

    # 1. 先修改所有import引用
    for file_path, changes in files_to_modify:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            new_content = content
            for filename, patterns in patterns_map.items():
                for pattern, replacement, desc in patterns:
                    new_content = re.sub(pattern, replacement, new_content)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            print(f"修改: {file_path}")
        except Exception as e:
            print(f"错误: 修改文件失败 {file_path}: {e}")

    # 2. 确保core目录和__init__.py存在
    ensure_core_init()

    # 3. 移动文件
    moved_files = move_files()

    print("\n" + "=" * 70)
    print("操作完成!")
    print(f"修改了 {len(files_to_modify)} 个文件")
    print(f"移动了 {len(moved_files)} 个文件到 {TARGET_DIR}/")
    print("=" * 70)

    # 打印注意事项
    print("\n注意事项:")
    print("1. 请检查修改后的文件是否正确")
    print("2. 运行测试确保功能正常")
    print("3. 如果有遗漏的引用，请手动修改")


if __name__ == "__main__":
    main()
