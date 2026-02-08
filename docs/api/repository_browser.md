# 仓库代码浏览 API 设计

## 文件树浏览

### GET /api/repositories/{repo_id}/tree

获取仓库的文件树结构。

#### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| repo_id | path | 是 | 仓库ID |
| ref | query | 否 | 分支名或提交SHA，默认 HEAD |
| path | query | 否 | 子目录路径，默认根目录 |

#### 响应

**200 OK**
```json
{
  "path": "src/components",
  "ref": "main",
  "entries": [
    {
      "name": "Button.vue",
      "type": "blob",
      "mode": "100644",
      "sha": "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391",
      "size": 1234
    },
    {
      "name": "Input",
      "type": "tree",
      "mode": "040000",
      "sha": "abc123..."
    }
  ]
}
```

**404 Not Found**
```json
{
  "detail": "Repository not found"
}
```

## 文件内容查看

### GET /api/repositories/{repo_id}/blob

获取文件内容。

#### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| repo_id | path | 是 | 仓库ID |
| ref | query | 否 | 分支名或提交SHA，默认 HEAD |
| path | query | 是 | 文件路径 |

#### 响应

**200 OK**
```json
{
  "path": "src/app.py",
  "ref": "main",
  "sha": "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391",
  "size": 1234,
  "content": "import os\n...",
  "encoding": "utf-8",
  "is_binary": false
}
```

**404 Not Found**
```json
{
  "detail": "File not found"
}
```

## 提交历史

### GET /api/repositories/{repo_id}/commits

获取提交历史。

#### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| repo_id | path | 是 | 仓库ID |
| ref | query | 否 | 分支名，默认主分支 |
| path | query | 否 | 特定文件的提交历史 |
| page | query | 否 | 页码，默认 1 |
| per_page | query | 否 | 每页数量，默认 30 |

#### 响应

**200 OK**
```json
{
  "commits": [
    {
      "sha": "abc123...",
      "message": "Initial commit",
      "author": {
        "name": "John Doe",
        "email": "john@example.com"
      },
      "date": "2024-01-01T00:00:00Z",
      "parents": ["def456..."]
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 30,
    "total": 100
  }
}
```

## 代码对比

### GET /api/repositories/{repo_id}/diff

获取代码差异。

#### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| repo_id | path | 是 | 仓库ID |
| base | query | 是 | 基准提交 |
| head | query | 是 | 对比提交 |
| path | query | 否 | 特定文件的差异 |

#### 响应

**200 OK**
```json
{
  "files": [
    {
      "path": "src/app.py",
      "status": "modified",
      "additions": 10,
      "deletions": 5,
      "chunks": [
        {
          "old_start": 1,
          "old_lines": 5,
          "new_start": 1,
          "new_lines": 10,
          "lines": [
            {"type": "context", "content": "import os"},
            {"type": "addition", "content": "import sys"},
            {"type": "deletion", "content": "import json"}
          ]
        }
      ]
    }
  ]
}
```
