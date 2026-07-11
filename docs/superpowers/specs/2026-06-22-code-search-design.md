# 代码搜索实现设计

> **日期**: 2026-06-22
> **阶段**: Phase 3 — 后端高级功能
> **任务 ID**: F-037 ~ F-039
> **开发方针**: TDD（测试驱动开发）

---

## 概述

为 Perseus 平台实现代码搜索功能，允许用户在仓库内搜索代码内容。基于 ripgrep 命令行工具，提供高效、准确的全文搜索能力。

## 设计目标

1. **高效搜索**：基于 ripgrep，性能优于纯 Python 实现
2. **简洁 API**：基础搜索参数，易于前端对接
3. **TDD 驱动**：所有功能先写测试，再实现
4. **与现有架构一致**：遵循 Utils → Service → Controller 分层

## 架构

```
┌─────────────────────────────────────────────────────────┐
│                    代码搜索模块                           │
├─────────────────────────────────────────────────────────┤
│  Controller          Service           Utils             │
│  ┌──────────┐       ┌──────────┐      ┌──────────────┐ │
│  │Search API│──────→│SearchSvc │─────→│ripgrep_utils │ │
│  │(GET /q)  │       │          │      │(subprocess)  │ │
│  └──────────┘       └──────────┘      └──────────────┘ │
│                           │                             │
│                     ┌──────────┐                        │
│                     │结果解析/  │                        │
│                     │格式化     │                        │
│                     └──────────┘                        │
└─────────────────────────────────────────────────────────┘
```

## 文件结构

```
perseus/
├── utils/ripgrep_utils.py           # ripgrep 命令封装
├── services/search_service.py       # 搜索业务逻辑
├── controller/search_controller.py  # 搜索 API 端点
└── tests/test_search_*.py           # TDD 测试
```

## 核心组件

### 1. Ripgrep Utils (`utils/ripgrep_utils.py`)

封装 ripgrep 命令行调用。

**方法：**
- `search_code(repo_path, query, path, ref) -> list[SearchResult]` — 执行搜索
- `is_available() -> bool` — 检查 ripgrep 是否可用

**依赖：**
- 系统需安装 ripgrep (`apt install ripgrep` 或 `brew install ripgrep`)

### 2. Search Service (`services/search_service.py`)

业务逻辑层。

**方法：**
- `search_code(repo_id, query, path, ref, db) -> SearchResponse` — 代码搜索

**响应模型：**
```python
@dataclass
class SearchResult:
    file: str       # 文件路径
    line: int       # 行号
    content: str    # 匹配行内容

@dataclass
class SearchResponse:
    query: str              # 搜索关键词
    results: list[SearchResult]  # 结果列表
    total_count: int        # 总匹配数
    truncated: bool         # 是否截断
```

### 3. Search Controller (`controller/search_controller.py`)

API 端点。

```
GET /api/v1/repositories/{repo_id}/search?q=关键词&path=目录&ref=分支
```

**参数：**
- `q` (必需): 搜索关键词
- `path` (可选): 限制搜索目录，默认搜索整个仓库
- `ref` (可选): Git 分支/标签/提交，默认为默认分支

**响应示例：**
```json
{
  "query": "def hello",
  "results": [
    {
      "file": "src/main.py",
      "line": 10,
      "content": "def hello():"
    }
  ],
  "total_count": 1,
  "truncated": false
}
```

## TDD 测试用例

### F-037: 仓库内全文搜索

| 测试 | 场景 |
|------|------|
| `test_search_code_in_repository()` | 在仓库中搜索代码 |
| `test_search_code_with_path_filter()` | 限制搜索目录 |
| `test_search_code_no_results()` | 无匹配结果 |
| `test_search_code_invalid_query()` | 无效搜索词 |

### F-038: 搜索结果格式

| 测试 | 场景 |
|------|------|
| `test_search_result_structure()` | 结果包含 file, line, content |
| `test_search_response_structure()` | 响应包含 query, results, total_count, truncated |
| `test_search_truncated_results()` | 结果超过限制时截断 |

### F-039: ripgrep 集成

| 测试 | 场景 |
|------|------|
| `test_ripgrep_available()` | 检查 ripgrep 可用 |
| `test_ripgrep_search()` | 执行搜索命令 |
| `test_ripgrep_not_found()` | ripgrep 未安装时降级 |

## 配置

```toml
[search]
enabled = true
max_results = 100
max_file_size = 10485760  # 10MB
```

## 依赖

- 无新 Python 依赖
- 系统依赖：ripgrep 命令行工具
- 需要在 Docker 镜像中安装 ripgrep

## 实施顺序

1. **TDD RED**: 编写所有测试用例
2. **TDD GREEN**: 实现 Ripgrep Utils → Service → Controller
3. **TDD REFACTOR**: 优化代码结构，消除重复
4. **验证**: 运行全部测试确认通过
