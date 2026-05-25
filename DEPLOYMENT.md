# EchoLens 2.0 部署指南

## 部署方式

EchoLens 2.0 支持多种部署方式：

### 1. Docker Compose 部署（推荐）

最简单的部署方式，适合生产环境。

```bash
# 克隆仓库
git clone https://github.com/your-org/echolens2.git
cd echolens2

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入必要的 API Key

# 启动服务
docker compose up -d

# 查看日志
docker compose logs -f

# 停止服务
docker compose down
```

访问 http://localhost:3000

### 2. 本地开发部署

适合开发和调试。

#### 后端

```bash
cd backend

# 创建虚拟环境
uv venv .venv

# 安装依赖
uv pip install --python .venv/Scripts/python.exe -e ".[dev]"

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件

# 运行测试
.venv/Scripts/python -m pytest -q

# 启动后端
.venv/Scripts/python run.py
```

后端运行在 http://localhost:5001

#### 前端

```bash
cd frontend

# 安装依赖
npm install

# 运行测试
npm run test
npm run test:e2e

# 启动开发服务器
npm run dev
```

前端运行在 http://localhost:3000

### 3. 桌面应用部署（Tauri）

构建跨平台桌面应用。

#### 环境要求

- **Rust**: >= 1.70
- **Node.js**: >= 18
- **Windows**: WebView2 Runtime
- **macOS**: macOS 10.15+
- **Linux**: webkit2gtk, libayatana-appindicator

#### 安装 Rust

```bash
# Windows
winget install Rustlang.Rustup

# macOS/Linux
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

#### 构建

```bash
cd frontend

# 开发模式（热重载）
npm run tauri:dev

# 生产构建
npm run tauri:build

# 调试构建
npm run tauri:build:debug
```

构建产物位于 `frontend/src-tauri/target/release/bundle/`：
- **Windows**: `.msi` / `.exe`
- **macOS**: `.dmg` / `.app`
- **Linux**: `.deb` / `.AppImage`

### 4. 移动应用部署（Capacitor）

构建 iOS 和 Android 应用。

#### 环境要求

- **Node.js**: >= 18
- **iOS**: Xcode 14+, CocoaPods
- **Android**: Android Studio, JDK 17+

#### 构建

```bash
cd frontend

# 构建 Web 资源
npm run build

# 同步到原生项目
npm run cap:sync

# iOS
npm run cap:open:ios
# 在 Xcode 中构建和运行

# Android
npm run cap:open:android
# 在 Android Studio 中构建和运行
```

## 环境变量配置

### 后端 `.env`

```bash
# LLM API 配置
LLM_API_KEY=your-api-key-here
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL_NAME=gpt-4o-mini

# Zep Cloud 配置（知识图谱）
ZEP_API_KEY=your-zep-api-key

# Flask 配置
FLASK_DEBUG=False
FLASK_ENV=production

# 数据库路径
DUCKDB_PATH=./data/echolens.duckdb

# 日志级别
LOG_LEVEL=INFO
```

### 前端 `.env`

```bash
# API 基础 URL（可选，默认使用平台抽象层自动配置）
VITE_API_BASE_URL=http://localhost:5001

# 构建目标（web / tauri / capacitor）
VITE_BUILD_TARGET=web
```

## 生产环境配置

### 1. 反向代理（Nginx）

```nginx
server {
    listen 80;
    server_name echolens.example.com;

    # 前端静态资源
    location / {
        root /var/www/echolens/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # 后端 API
    location /api {
        proxy_pass http://localhost:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # SSE 支持
    location /api/stream {
        proxy_pass http://localhost:5001;
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        chunked_transfer_encoding off;
        proxy_buffering off;
        proxy_cache off;
    }
}
```

### 2. HTTPS 配置（Let's Encrypt）

```bash
# 安装 Certbot
sudo apt install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d echolens.example.com

# 自动续期
sudo certbot renew --dry-run
```

### 3. 进程管理（systemd）

#### 后端服务

创建 `/etc/systemd/system/echolens-backend.service`：

```ini
[Unit]
Description=EchoLens Backend
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/echolens/backend
Environment="PATH=/var/www/echolens/backend/.venv/bin"
ExecStart=/var/www/echolens/backend/.venv/bin/python run.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable echolens-backend
sudo systemctl start echolens-backend
sudo systemctl status echolens-backend
```

### 4. 数据库备份

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/var/backups/echolens"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 备份 DuckDB
cp /var/www/echolens/backend/data/echolens.duckdb \
   $BACKUP_DIR/echolens_$TIMESTAMP.duckdb

# 保留最近 7 天的备份
find $BACKUP_DIR -name "echolens_*.duckdb" -mtime +7 -delete
```

添加到 crontab：

```bash
# 每天凌晨 2 点备份
0 2 * * * /var/www/echolens/scripts/backup.sh
```

## 性能优化

### 1. 前端优化

- ✅ 代码分割（已实现）
- ✅ 懒加载路由（已实现）
- ✅ Gzip 压缩（Nginx 配置）
- 🚧 CDN 加速（可选）
- 🚧 Service Worker 缓存（可选）

### 2. 后端优化

- 使用 Gunicorn 多进程部署
- 配置 Redis 缓存
- 数据库连接池
- 异步任务队列（Celery）

```bash
# Gunicorn 部署
pip install gunicorn

gunicorn -w 4 -b 0.0.0.0:5001 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile - \
  run:app
```

## 监控和日志

### 1. 应用监控

推荐使用：
- **Sentry**: 错误追踪
- **Prometheus + Grafana**: 性能监控
- **ELK Stack**: 日志聚合

### 2. 健康检查

```bash
# 后端健康检查
curl http://localhost:5001/api/health

# 前端健康检查
curl http://localhost:3000
```

## 故障排查

### 后端无法启动

1. 检查环境变量：`cat .env`
2. 检查依赖：`.venv/Scripts/python -m pip list`
3. 检查日志：`tail -f logs/app.log`
4. 检查端口占用：`netstat -ano | findstr 5001`

### 前端构建失败

1. 清理缓存：`npm run clean && npm install`
2. 检查 Node 版本：`node --version`（需要 >= 18）
3. 检查磁盘空间：`df -h`

### 数据库错误

1. 检查文件权限：`ls -la data/echolens.duckdb`
2. 检查磁盘空间
3. 尝试重建：删除 `.duckdb` 文件后重启

### 跨平台构建失败

#### Tauri

1. 检查 Rust：`rustc --version`
2. 更新 Rust：`rustup update`
3. 清理缓存：`cargo clean`

#### Capacitor

1. 检查 Xcode / Android Studio 安装
2. 清理原生项目：删除 `ios/` 和 `android/` 后重新 `cap add`
3. 检查 CocoaPods：`pod --version`

## 安全建议

1. **API Key 保护**：不要将 API Key 提交到版本控制
2. **HTTPS**：生产环境必须使用 HTTPS
3. **CORS 配置**：限制允许的来源域名
4. **输入验证**：后端严格验证所有输入
5. **定期更新**：及时更新依赖包修复安全漏洞

## 扩展阅读

- [Docker 官方文档](https://docs.docker.com/)
- [Tauri 部署指南](https://tauri.app/v1/guides/building/)
- [Capacitor 部署指南](https://capacitorjs.com/docs/deployment)
- [Nginx 配置最佳实践](https://www.nginx.com/resources/wiki/)
