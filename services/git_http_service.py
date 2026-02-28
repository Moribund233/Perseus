"""
Git HTTP 服务层

本模块通过调用 git http-backend CGI 程序实现 Git Smart HTTP 协议，
支持标准的 git clone/push/pull 操作。
"""
import os
import re
import asyncio
import subprocess
from typing import Optional, Tuple, Dict, Any
from pathlib import Path

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exception import NotFoundException, AuthorizationException
from models import Repository, User
from models.repository_member import RepositoryMember
from utils.git_utils import get_repository_storage_path, repo_exists


# =============================================================================
# 异常定义
# =============================================================================

class GitHttpError(Exception):
    """Git HTTP 协议错误"""
    pass


class GitHttpBackendError(Exception):
    """Git HTTP Backend 执行错误"""
    pass


# =============================================================================
# 权限和仓库查询函数
# =============================================================================

def get_repo_physical_path(repo_path: str) -> str:
    """
    获取仓库的物理存储路径
    
    Args:
        repo_path: 仓库路径（如 username/repo-name）
        
    Returns:
        str: 物理存储路径
    """
    return get_repository_storage_path(repo_path)


def check_repository_exists(repo_path: str) -> bool:
    """
    检查仓库是否存在
    
    Args:
        repo_path: 仓库路径
        
    Returns:
        bool: 仓库是否存在
    """
    physical_path = get_repo_physical_path(repo_path)
    return repo_exists(physical_path)


async def get_repository_by_path(repo_path: str, db: AsyncSession) -> Optional[Repository]:
    """
    根据路径获取仓库

    支持标准格式: username/repo-name

    Args:
        repo_path: 仓库路径（如 username/repo-name）
        db: 异步数据库会话

    Returns:
        Repository: 仓库对象，不存在则返回 None
    """
    if not repo_path:
        return None

    # 标准化路径：移除前导和尾随的 /
    normalized_path = repo_path.strip('/')

    # 尝试直接匹配路径
    result = await db.execute(select(Repository).filter(Repository.path == normalized_path))
    repo = result.scalar_one_or_none()
    if repo:
        return repo

    # 尝试匹配 {username}/{repo_name} 格式
    parts = normalized_path.split('/')
    if len(parts) >= 2:
        username = parts[0]  # 第一部分作为用户名
        repo_name = parts[1]  # 第二部分作为仓库名
        result = await db.execute(select(User).filter(User.username == username))
        user = result.scalar_one_or_none()
        if user:
            result = await db.execute(
                select(Repository).filter(
                    Repository.owner_id == user.id,
                    Repository.name == repo_name
                )
            )
            repo = result.scalar_one_or_none()
            if repo:
                return repo

    return None


async def check_git_permission(repo_path: str, user: Optional[User], action: str, db: AsyncSession) -> bool:
    """
    检查用户是否有 Git 操作权限
    
    权限规则：
    - 公开仓库：允许任何人读取
    - 私有仓库：只有成员可以读取
    - 写入权限：只有 owner、admin 和 developer 角色可以写入
    
    Args:
        repo_path: 仓库路径
        user: 用户对象，None 表示匿名用户
        action: 操作类型，"read" 或 "write"
        db: 异步数据库会话
        
    Returns:
        bool: 是否有权限
    """
    repo = await get_repository_by_path(repo_path, db)
    if not repo:
        return False

    # 公开仓库允许任何人读取
    if repo.is_public and action == "read":
        return True

    # 匿名用户只能访问公开仓库
    if not user:
        return False

    # 仓库所有者拥有所有权限
    if repo.owner_id == user.id:
        return True

    # 检查成员权限
    result = await db.execute(
        select(RepositoryMember).filter(
            RepositoryMember.repository_id == repo.id,
            RepositoryMember.user_id == user.id
        )
    )
    member = result.scalar_one_or_none()

    if not member or not member.is_active:
        return False

    if action == "read":
        return True
    elif action == "write":
        # owner, admin 和 developer 角色可以写入
        return member.role in ["owner", "admin", "developer"]

    return False


def parse_service_name(service: str) -> str:
    """
    解析 Git 服务名称
    
    Args:
        service: 服务参数值（如 "git-upload-pack"）
        
    Returns:
        str: 服务名称（如 "upload-pack"）
        
    Raises:
        GitHttpError: 无效的服务名称
    """
    if not service.startswith("git-"):
        raise GitHttpError("Invalid service name")

    service_name = service[4:]  # 去掉 "git-" 前缀
    if service_name not in ["upload-pack", "receive-pack"]:
        raise GitHttpError("Unsupported service")

    return service_name


# =============================================================================
# Git HTTP Backend 服务类
# =============================================================================

class GitHttpBackendService:
    """
    Git HTTP Backend 服务类
    
    通过调用 Git 官方的 `git http-backend` CGI 程序来处理 Git HTTP 请求。
    
    说明：
    ------
    git http-backend 是 Git 官方提供的 CGI 程序，实现了完整的 Git Smart HTTP 协议。
    它自动处理以下复杂逻辑：
    - 引用发现（refs discovery）
    - packfile 生成和压缩
    - 推送接收和验证
    - 协议协商和能力声明
    
    使用方式：
    ----------
    1. 设置必要的环境变量（GIT_PROJECT_ROOT, PATH_INFO 等）
    2. 调用 git http-backend 进程
    3. 将 HTTP 请求体传递给进程
    4. 读取进程的输出作为 HTTP 响应
    
    环境变量：
    ----------
    - GIT_PROJECT_ROOT: 仓库根目录（所有仓库的父目录）
    - PATH_INFO: 请求路径（相对于 GIT_PROJECT_ROOT）
    - QUERY_STRING: URL 查询参数
    - REQUEST_METHOD: HTTP 方法（GET/POST）
    - REMOTE_USER: 认证用户（可选）
    
    参考：
    ------
    - https://git-scm.com/docs/git-http-backend
    - https://git-scm.com/book/en/v2/Git-on-the-Server-Smart-HTTP
    """
    
    def __init__(self):
        """初始化服务，检查 git http-backend 是否可用"""
        self._git_backend_path = self._find_git_http_backend()
        if not self._git_backend_path:
            raise GitHttpBackendError(
                "git http-backend not found. Please ensure Git is installed and available in PATH."
            )
    
    def _find_git_http_backend(self) -> Optional[str]:
        """
        查找 git http-backend 可执行文件路径
        
        现代 Git 版本中，直接调用 `git http-backend` 即可，
        Git 会自动在 exec-path 中找到正确的可执行文件。
        
        Returns:
            str: 返回 'git' 表示通过 git 命令调用，未找到返回 None
        """
        # 检查 git 命令是否可用
        try:
            result = subprocess.run(
                ['git', '--version'],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                return 'git'
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        return None
    
    def _prepare_environment(
        self,
        repo_path: str,
        request: Request,
        content_length: int = 0,
        remote_user: Optional[str] = None
    ) -> Tuple[Dict[str, str], str]:
        """
        准备 git http-backend 的环境变量

        设置 CGI 标准环境变量和 Git 特定变量。
        遵循 Gitee/GitHub 标准 URL 格式: /{username}/{repo_name}.git/info/refs

        Args:
            repo_path: 仓库路径（如 username/repo-name）
            request: HTTP 请求对象
            content_length: 请求体长度
            remote_user: 远程用户名（可选）

        Returns:
            Tuple[Dict[str, str], str]: (环境变量字典, 仓库根目录路径)
        """
        env = os.environ.copy()

        # GIT_PROJECT_ROOT 是仓库根目录（所有仓库的父目录）
        # 从配置读取，确保与 get_repository_storage_path 使用相同的配置
        from utils.config_utils import get_config_manager
        config_manager = get_config_manager()
        repo_root = config_manager.get("storage.repo_root", "./repositories")
        repo_root = os.path.abspath(repo_root)

        # 构建 PATH_INFO
        # 标准 URL 格式: /{username}/{repo_name}.git/info/refs
        # 需要转换为: /{username}/{repo_name}/info/refs（去掉 .git 后缀）
        request_path = request.url.path

        # 确保 path_info 以 / 开头（CGI 标准要求）
        if not request_path.startswith('/'):
            request_path = '/' + request_path

        # 移除 .git 后缀（从仓库名部分）
        # 如: /username/repo.git/info/refs -> /username/repo/info/refs
        path_info = self._normalize_path_info(request_path)

        # 设置 CGI 环境变量
        env.update({
            # Git 特定变量
            'GIT_PROJECT_ROOT': repo_root,
            'GIT_HTTP_EXPORT_ALL': '1',  # 允许访问所有仓库

            # CGI 标准变量
            'PATH_INFO': path_info,
            'QUERY_STRING': str(request.query_params),
            'REQUEST_METHOD': request.method,
            'CONTENT_TYPE': request.headers.get('content-type', ''),
            'CONTENT_LENGTH': str(content_length),
            'SCRIPT_NAME': '',  # 根路径挂载，SCRIPT_NAME 为空
            'SERVER_NAME': request.url.hostname or 'localhost',
            'SERVER_PORT': str(request.url.port or 80),
            'SERVER_PROTOCOL': 'HTTP/1.1',
            'SERVER_SOFTWARE': 'LanGit/0.1.0',

            # HTTP 头变量
            'HTTP_HOST': request.headers.get('host', ''),
            'HTTP_USER_AGENT': request.headers.get('user-agent', ''),
            'HTTP_ACCEPT': request.headers.get('accept', '*/*'),
            'HTTP_ACCEPT_ENCODING': request.headers.get('accept-encoding', ''),
            'HTTP_ACCEPT_LANGUAGE': request.headers.get('accept-language', ''),
            'HTTP_CONNECTION': request.headers.get('connection', ''),
        })

        # 添加认证信息
        if remote_user:
            env['REMOTE_USER'] = remote_user
            env['AUTH_TYPE'] = 'Basic'
        else:
            env['REMOTE_USER'] = ''
            env['AUTH_TYPE'] = ''

        # 转发其他 HTTP 头
        for header_name, header_value in request.headers.items():
            env_header_name = f'HTTP_{header_name.upper().replace("-", "_")}'
            if env_header_name not in env:
                env[env_header_name] = header_value

        return env, repo_root

    def _normalize_path_info(self, path: str) -> str:
        """
        标准化 PATH_INFO，移除 .git 后缀

        Git HTTP 标准 URL 格式为 /{username}/{repo_name}.git/info/refs
        git http-backend 期望的路径格式为 /{username}/{repo_name}/info/refs

        Args:
            path: 原始请求路径，如 /username/repo.git/info/refs

        Returns:
            str: 标准化后的路径，如 /username/repo/info/refs
        """
        if not path.startswith('/'):
            path = '/' + path

        parts = path.strip('/').split('/')
        if len(parts) >= 2:
            # 第二部分应该是仓库名，可能带有 .git 后缀
            repo_name = parts[1]
            if repo_name.endswith('.git'):
                parts[1] = repo_name[:-4]  # 移除 .git 后缀
                path = '/' + '/'.join(parts)

        return path
    
    def _parse_cgi_response(self, stdout: bytes) -> Tuple[int, Dict[str, str], bytes]:
        """
        解析 CGI 响应
        
        git http-backend 的输出格式：
        ```
        Status: 200 OK\r\n
        Content-Type: application/x-git-upload-pack-advertisement\r\n
        \r\n
        <body data>
        ```
        
        Args:
            stdout: git http-backend 的输出
            
        Returns:
            Tuple[int, Dict[str, str], bytes]: (状态码, 响应头, 响应体)
        """
        # 查找头和体的分隔（双换行）
        header_end = stdout.find(b'\r\n\r\n')
        if header_end == -1:
            header_end = stdout.find(b'\n\n')
            if header_end == -1:
                # 没有分隔符，全部作为响应体
                return 200, {}, stdout
            header_bytes = stdout[:header_end]
            body = stdout[header_end + 2:]
        else:
            header_bytes = stdout[:header_end]
            body = stdout[header_end + 4:]
        
        # 解析响应头
        headers = {}
        status_code = 200
        
        try:
            header_text = header_bytes.decode('utf-8', errors='ignore')
            for line in header_text.split('\n'):
                line = line.strip()
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    headers[key] = value
                    
                    # 提取状态码
                    if key.lower() == 'status':
                        status_match = re.match(r'(\d+)', value)
                        if status_match:
                            status_code = int(status_match.group(1))
        except Exception:
            pass
        
        return status_code, headers, body
    
    async def handle_request(
        self,
        repo_path: str,
        request: Request,
        body: Optional[bytes] = None,
        remote_user: Optional[str] = None
    ) -> Tuple[int, Dict[str, str], bytes]:
        """
        处理 Git HTTP 请求
        
        这是主要的入口方法，通过调用 git http-backend 来处理 Git 请求。
        
        处理流程：
        1. 验证仓库是否存在
        2. 准备 CGI 环境变量
        3. 启动 git http-backend 子进程
        4. 发送请求体（如果有）
        5. 读取响应
        6. 解析并返回结果
        
        Args:
            repo_path: 仓库路径（如 username/repo-name）
            request: HTTP 请求对象
            body: 请求体数据（POST 请求需要）
            remote_user: 远程用户名（可选）
            
        Returns:
            Tuple[int, Dict[str, str], bytes]: (状态码, 响应头, 响应体)
            
        Raises:
            NotFoundException: 仓库不存在
            GitHttpBackendError: 处理失败
        """
        # 获取物理路径
        physical_path = get_repo_physical_path(repo_path)
        
        if not repo_exists(physical_path):
            raise NotFoundException(detail="Repository not found")
        
        # 确保仓库目录以 .git 结尾（git http-backend 的要求）
        if not physical_path.endswith('.git'):
            physical_path_with_git = physical_path + '.git'
            if os.path.exists(physical_path_with_git):
                physical_path = physical_path_with_git
        
        # 准备环境变量
        content_length = len(body) if body else 0
        env, repo_root = self._prepare_environment(physical_path, request, content_length, remote_user)

        try:
            # 使用 asyncio 创建异步子进程
            # 这样可以避免阻塞 FastAPI 的事件循环，支持高并发
            # cwd 设置为 GIT_PROJECT_ROOT，让 git http-backend 能正确解析 PATH_INFO
            process = await asyncio.create_subprocess_exec(
                self._git_backend_path, 'http-backend',
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=repo_root
            )
            
            # 设置超时
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(input=body),
                    timeout=300  # 5分钟超时
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise GitHttpBackendError("Request timeout")
            
            if process.returncode != 0:
                stderr_text = stderr.decode('utf-8', errors='ignore') if stderr else 'Unknown error'
                raise GitHttpBackendError(f"git http-backend failed: {stderr_text}")
            
            # 解析响应
            status_code, headers, response_body = self._parse_cgi_response(stdout)
            
            return status_code, headers, response_body
            
        except GitHttpBackendError:
            raise
        except Exception as e:
            raise GitHttpBackendError(f"Failed to execute git http-backend: {str(e)}")


# =============================================================================
# 单例实例和工厂函数
# =============================================================================

git_backend_service: Optional[GitHttpBackendService] = None


def get_git_backend_service() -> GitHttpBackendService:
    """
    获取 GitHttpBackendService 单例实例
    
    Returns:
        GitHttpBackendService: 服务实例
    """
    global git_backend_service
    if git_backend_service is None:
        git_backend_service = GitHttpBackendService()
    return git_backend_service
