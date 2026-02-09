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
      "path": "src/components/Button.vue",
      "sha": "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391",
      "mode": 33188,
      "size": 1234
    },
    {
      "name": "Input",
      "type": "tree",
      "path": "src/components/Input",
      "sha": "abc123...",
      "mode": 16384
    }
  ]
}
```

**响应字段说明**

| 字段 | 类型 | 说明 |
|------|------|------|
| path | string | 当前路径 |
| ref | string | 引用的分支或提交 |
| entries | array | 文件/目录条目列表 |
| entries[].name | string | 文件/目录名称 |
| entries[].type | string | 类型：blob(文件) 或 tree(目录) |
| entries[].path | string | 完整路径 |
| entries[].sha | string | 对象SHA |
| entries[].mode | int | 文件模式（十进制） |
| entries[].size | int | 文件大小（字节，仅文件类型） |

**404 Not Found**
```json
{
  "detail": "Repository not found"
}
```

---

## 文件内容查看

### GET /api/repositories/{repo_id}/blob

获取文件内容。

#### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| repo_id | path | 是 | 仓库ID |
| path | query | 是 | 文件路径 |
| ref | query | 否 | 分支名或提交SHA，默认 HEAD |

#### 响应

**200 OK**
```json
{
  "name": "app.py",
  "path": "src/app.py",
  "sha": "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391",
  "ref": "main",
  "content": "import os\n...",
  "size": 1234,
  "encoding": "utf-8",
  "is_binary": false
}
```

**响应字段说明**

| 字段 | 类型 | 说明 |
|------|------|------|
| name | string | 文件名 |
| path | string | 文件路径 |
| sha | string | 文件对象SHA |
| ref | string | 引用的分支或提交 |
| content | string | 文件内容（二进制文件为hex编码） |
| size | int | 文件大小（字节） |
| encoding | string | 编码方式：utf-8 或 hex |
| is_binary | boolean | 是否为二进制文件 |

**404 Not Found**
```json
{
  "detail": "File not found"
}
```

---

## 提交历史

### GET /api/repositories/{repo_id}/commits

获取提交历史。

#### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| repo_id | path | 是 | 仓库ID |
| ref | query | 否 | 分支名，默认 HEAD |
| path | query | 否 | 特定文件的提交历史 |
| page | query | 否 | 页码，默认 1 |
| per_page | query | 否 | 每页数量，默认 30，最大 100 |

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
        "email": "john@example.com",
        "date": "2024-01-01T00:00:00"
      },
      "committer": {
        "name": "John Doe",
        "email": "john@example.com",
        "date": "2024-01-01T00:00:00"
      },
      "date": "2024-01-01T00:00:00",
      "parents": ["def456..."]
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 30
  }
}
```

**响应字段说明**

| 字段 | 类型 | 说明 |
|------|------|------|
| commits | array | 提交列表 |
| commits[].sha | string | 提交SHA |
| commits[].message | string | 提交信息 |
| commits[].author | object | 作者信息 |
| commits[].author.name | string | 作者名称 |
| commits[].author.email | string | 作者邮箱 |
| commits[].author.date | string | 作者日期（ISO格式） |
| commits[].committer | object | 提交者信息（字段同 author） |
| commits[].date | string | 提交日期（ISO格式） |
| commits[].parents | array | 父提交SHA列表 |
| pagination | object | 分页信息 |
| pagination.page | int | 当前页码 |
| pagination.per_page | int | 每页数量 |

**404 Not Found**
```json
{
  "detail": "Repository not found"
}
```

---

## 代码对比

### GET /api/repositories/{repo_id}/diff

获取代码差异。

#### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| repo_id | path | 是 | 仓库ID |
| head | query | 是 | 对比提交SHA |
| base | query | 否 | 基准提交SHA，默认与空树对比 |
| path | query | 否 | 特定文件的差异 |

#### 响应

**200 OK**
```json
{
  "files": [
    {
      "old_path": "src/app.py",
      "new_path": "src/app.py",
      "status": "M",
      "additions": 10,
      "deletions": 5,
      "hunks": [
        {
          "old_start": 1,
          "old_lines": 5,
          "new_start": 1,
          "new_lines": 10,
          "lines": [
            {
              "origin": " ",
              "content": "import os"
            },
            {
              "origin": "+",
              "content": "import sys"
            },
            {
              "origin": "-",
              "content": "import json"
            }
          ]
        }
      ]
    }
  ],
  "stats": {
    "files_changed": 1,
    "additions": 10,
    "deletions": 5
  }
}
```

**响应字段说明**

| 字段 | 类型 | 说明 |
|------|------|------|
| files | array | 变更文件列表 |
| files[].old_path | string | 原文件路径 |
| files[].new_path | string | 新文件路径 |
| files[].status | string | 变更状态：A(新增), D(删除), M(修改), R(重命名) 等 |
| files[].additions | int | 新增行数 |
| files[].deletions | int | 删除行数 |
| files[].hunks | array | 代码块列表 |
| files[].hunks[].old_start | int | 原文件起始行号 |
| files[].hunks[].old_lines | int | 原文件行数 |
| files[].hunks[].new_start | int | 新文件起始行号 |
| files[].hunks[].new_lines | int | 新文件行数 |
| files[].hunks[].lines | array | 代码行列表 |
| files[].hunks[].lines[].origin | string | 行类型：空格(上下文), +(新增), -(删除) |
| files[].hunks[].lines[].content | string | 行内容 |
| stats | object | 统计信息 |
| stats.files_changed | int | 变更文件数 |
| stats.additions | int | 总行数增加 |
| stats.deletions | int | 总行数删除 |

**404 Not Found**
```json
{
  "detail": "Commit not found"
}
```

---

## 错误响应

所有接口在发生错误时返回统一的错误格式：

```json
{
  "detail": "错误描述信息"
}
```

### 常见错误码

| HTTP状态码 | 说明 |
|------------|------|
| 400 | 请求参数错误（如缺少必填参数） |
| 404 | 资源不存在（仓库、文件、提交等） |
| 422 | 请求格式正确但语义错误（如路径是目录而非文件） |
| 500 | 服务器内部错误 |
