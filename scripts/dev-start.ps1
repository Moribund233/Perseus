# =============================================================================
# Perseus 开发环境启动脚本 (PowerShell)
#
# 功能:
#   - 检查环境变量配置
#   - 构建并启动 Docker 服务
#   - 提供常用命令快捷方式
#
# 使用方法:
#   .\scripts\dev-start.ps1          # 启动所有服务
#   .\scripts\dev-start.ps1 build    # 强制重新构建镜像
#   .\scripts\dev-start.ps1 stop     # 停止服务
#   .\scripts\dev-start.ps1 logs     # 查看日志
#   .\scripts\dev-start.ps1 shell    # 进入后端容器
#   .\scripts\dev-start.ps1 clean    # 停止并清除所有数据
# =============================================================================

param(
    [Parameter(Position = 0)]
    [string]$Command = "start"
)

$ErrorActionPreference = "Stop"
$ComposeFile = "docker-compose.dev.yml"

# 颜色定义
$Green = "`e[32m"
$Yellow = "`e[33m"
$Red = "`e[31m"
$Blue = "`e[34m"
$Reset = "`e[0m"

function Write-Info($message) {
    Write-Host "${Blue}[INFO]${Reset} $message"
}

function Write-Success($message) {
    Write-Host "${Green}[OK]${Reset} $message"
}

function Write-Warning($message) {
    Write-Host "${Yellow}[WARN]${Reset} $message"
}

function Write-Error($message) {
    Write-Host "${Red}[ERROR]${Reset} $message"
}

function Test-EnvFile {
    if (-not (Test-Path ".env")) {
        Write-Warning ".env 文件不存在"
        Write-Info "正在从 .env.dev 创建 .env..."
        Copy-Item ".env.dev" ".env"
        Write-Success ".env 文件已创建"
        Write-Warning "请编辑 .env 文件，设置 PERSEUS_SECURITY_SECRET_KEY 密钥后再启动"
        exit 1
    }

    # 检查密钥是否已修改
    $envContent = Get-Content ".env" -Raw
    if ($envContent -match "PERSEUS_SECURITY_SECRET_KEY=your-secret-key-here") {
        Write-Error "请修改 .env 文件中的 PERSEUS_SECURITY_SECRET_KEY 密钥！"
        Write-Info "生成密钥命令: openssl rand -hex 32"
        exit 1
    }
}

function Start-DevEnvironment {
    Write-Info "检查环境配置..."
    Test-EnvFile

    Write-Info "启动 Perseus 开发环境..."
    Write-Info "Docker Compose 文件: $ComposeFile"

    # 检查 Docker 是否运行
    try {
        $null = docker info 2>$null
    }
    catch {
        Write-Error "Docker 未运行，请先启动 Docker Desktop"
        exit 1
    }

    # 构建并启动服务
    docker compose -f $ComposeFile up -d --build

    if ($LASTEXITCODE -eq 0) {
        Write-Success "服务启动成功！"
        Write-Host ""
        Write-Host "访问地址:"
        Write-Host "  - 前端:       http://localhost:5173 (请在 client/web 目录运行 pnpm dev)"
        Write-Host "  - API 文档:   http://localhost:8080/docs"
        Write-Host "  - API:        http://localhost:8080/api"
        Write-Host "  - 数据库:     localhost:5432"
        Write-Host ""
        Write-Host "常用命令:"
        Write-Host "  - 查看日志:   .\scripts\dev-start.ps1 logs"
        Write-Host "  - 进入容器:   .\scripts\dev-start.ps1 shell"
        Write-Host "  - 停止服务:   .\scripts\dev-start.ps1 stop"
        Write-Host ""
        Write-Info "正在显示日志..."
        docker compose -f $ComposeFile logs -f
    }
    else {
        Write-Error "服务启动失败"
        exit 1
    }
}

function Stop-DevEnvironment {
    Write-Info "停止 Perseus 开发环境..."
    docker compose -f $ComposeFile down
    Write-Success "服务已停止"
}

function Show-Logs {
    Write-Info "显示服务日志..."
    docker compose -f $ComposeFile logs -f
}

function Enter-Shell {
    Write-Info "进入后端容器..."
    docker compose -f $ComposeFile exec app bash
}

function Clear-Environment {
    Write-Warning "这将停止服务并删除所有数据卷！"
    $confirm = Read-Host "确认继续? (y/N)"
    if ($confirm -eq "y" -or $confirm -eq "Y") {
        docker compose -f $ComposeFile down -v
        Write-Success "环境已清理"
    }
    else {
        Write-Info "已取消"
    }
}

function Rebuild-Images {
    Write-Info "强制重新构建镜像..."
    docker compose -f $ComposeFile build --no-cache
    Write-Success "镜像构建完成"
    Start-DevEnvironment
}

# 主逻辑
switch ($Command.ToLower()) {
    "start" { Start-DevEnvironment }
    "build" { Rebuild-Images }
    "stop" { Stop-DevEnvironment }
    "logs" { Show-Logs }
    "shell" { Enter-Shell }
    "clean" { Clear-Environment }
    default {
        Write-Host "Perseus 开发环境管理脚本"
        Write-Host ""
        Write-Host "用法: .\scripts\dev-start.ps1 [命令]"
        Write-Host ""
        Write-Host "命令:"
        Write-Host "  start  - 启动开发环境 (默认)"
        Write-Host "  build  - 重新构建镜像并启动"
        Write-Host "  stop   - 停止服务"
        Write-Host "  logs   - 查看日志"
        Write-Host "  shell  - 进入后端容器"
        Write-Host "  clean  - 停止并清除所有数据"
    }
}
