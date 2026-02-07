# LanGit 打包指南

本指南描述了如何将前端构建文件包含到FastAPI应用的可执行文件中，实现前后端一体化部署。

## 1. 前端构建文件存放位置

### 1.1 前端构建配置

Vite项目默认的构建输出目录是`dist`。在`frontend`目录下执行构建命令后，所有静态文件会生成在`frontend/dist`目录下。

### 1.2 构建前端项目

```bash
cd frontend
npm run build
```

构建完成后，前端文件将生成在以下目录：
```
d:\Project\Python\LanGit\frontend\dist
```

## 2. 修改FastAPI应用，添加静态文件服务

需要修改`app.py`文件，添加静态文件服务配置，让FastAPI能够提供前端静态文件。

### 2.1 修改`app.py`文件

```python
import sys
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# 获取当前应用的根目录
if getattr(sys, 'frozen', False):
    # 打包后，sys._MEIPASS指向临时目录
    APP_ROOT = Path(sys._MEIPASS)
else:
    # 开发模式，使用当前目录
    APP_ROOT = Path(__file__).parent

# 在create_app函数中添加以下代码

def create_app(config_path: str = "config.toml") -> FastAPI:
    # ... 现有代码 ...
    
    # 配置静态文件目录
    static_dir = APP_ROOT / "frontend" / "dist"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    
    # 添加前端入口路由
    @app.get("/")
    async def index():
        return FileResponse(str(static_dir / "index.html"))
    
    @app.get("/{path:path}")
    async def catch_all(path: str):
        # 处理单页应用的路由，返回index.html
        return FileResponse(str(static_dir / "index.html"))
    
    # ... 现有代码 ...
```

## 3. 修改PyInstaller配置文件

需要修改`langit_desktop.spec`文件，将前端构建文件添加到资源列表中。

### 3.1 修改`langit_desktop.spec`文件

```python
# 定义要包含的文件和目录
datas = [
    ('client/desktop/ui/icons/logo.ico', 'client/desktop/ui/icons'),
    # 添加前端构建文件
    ('frontend/dist', 'frontend/dist'),
]
```

## 4. 完整的构建和打包流程

### 4.1 构建前端项目

```bash
cd frontend
npm install
npm run build
```

### 4.2 打包客户端应用

```bash
# 确保已安装PyInstaller
pip install pyinstaller

# 执行打包命令
pyinstaller langit_desktop.spec
```

### 4.3 打包结果

打包完成后，可执行文件将生成在`dist`目录下：
```
d:\Project\Python\LanGit\dist\LanGit.exe
```

## 5. 注意事项

1. **前端资源引用路径**：确保前端构建后的`index.html`中所有资源引用路径都是相对路径或使用`/static/`前缀

2. **开发模式**：在开发模式下，FastAPI会直接从项目目录读取静态文件，无需额外配置

3. **生产模式**：在生产模式下，PyInstaller会将静态文件打包到可执行文件中，并在运行时解压到临时目录

4. **静态文件目录结构**：确保前端构建后的目录结构保持一致，避免因目录结构变化导致的静态文件加载失败

5. **CORS配置**：如果前端和后端分离部署，需要在`app.py`中配置正确的CORS规则

6. **端口配置**：确保服务器端口配置正确，避免端口冲突

## 6. 开发阶段与生产阶段的区别

### 6.1 开发阶段

- 前端可以通过Vite开发服务器独立运行（默认端口：5173）
- FastAPI后端运行在独立端口（默认端口：8000）
- 前后端通过API进行通信
- 无需配置静态文件服务

### 6.2 生产阶段

- 前端构建成静态文件
- 静态文件被打包到可执行文件中
- FastAPI同时提供API服务和静态文件服务
- 前后端一体化部署，用户只需运行一个可执行文件

## 7. 常见问题及解决方案

### 7.1 静态文件加载失败

**问题**：打包后，前端页面无法加载静态资源

**解决方案**：
- 检查静态文件是否正确包含在PyInstaller配置中
- 检查FastAPI的静态文件配置是否正确
- 检查前端资源引用路径是否使用了正确的前缀

### 7.2 前端路由无法访问

**问题**：打包后，直接访问前端路由（如`/home`）返回404

**解决方案**：
- 确保添加了`catch_all`路由，将所有未匹配的请求重定向到`index.html`

### 7.3 打包后的可执行文件过大

**问题**：打包后的可执行文件体积过大

**解决方案**：
- 优化PyInstaller配置，排除不必要的依赖
- 使用`upx`工具压缩可执行文件
- 考虑使用虚拟环境，减少依赖数量

## 8. 后续计划

1. 编写自动化构建脚本，简化构建和打包流程
2. 优化静态文件加载性能
3. 添加更多的打包配置选项，支持不同环境的部署需求
4. 编写测试脚本，验证打包后的应用功能是否正常

本指南将随着项目的发展不断更新和完善。