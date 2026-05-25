# EchoLens 2.0 — Deployment & Cross-Platform Guide

EchoLens 是 Flask 3 后端 + Vue 3 前端的双进程应用。本文档覆盖 4 条交付路线：

1. **Docker Compose**（生产，单台主机）
2. **Web 静态部署**（前端走 CDN，后端走 K8s / VM）
3. **Tauri Desktop**（Windows / macOS / Linux 桌面包，scaffold 已就位）
4. **Capacitor Android**（Android APK / AAB，scaffold 已就位）

iOS 不在本里程碑范围内。

---

## 0. 前置：环境变量

后端 `.env`（部署到容器或 systemd 时通过 secret 注入，**不可入 git**）：

```
LLM_API_KEY=
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL_NAME=gpt-4o-mini
KUZU_DB_PATH=/var/lib/echolens/kuzu_db
DUCKDB_PATH=/var/lib/echolens/echolens.duckdb
UPLOAD_DIR=/var/lib/echolens/uploads
LOG_LEVEL=INFO
```

前端构建期变量：

| 变量 | 取值 | 作用 |
|---|---|---|
| `VITE_BUILD_TARGET` | `web` (默认) / `tauri` / `capacitor` | 控制 `vite.config.ts` 的 `base` —— web 用 `/`，桌面/移动用 `./` |

---

## 1. Docker Compose（推荐：单机生产）

```bash
docker compose up -d --build
```

- 后端：`backend/Dockerfile` → Flask + gunicorn，绑定 5001。
- 前端：`frontend/Dockerfile` → 多阶段，`npm run build` + nginx。
- 持久卷：`./data/kuzu_db`、`./data/duckdb`、`./data/uploads`。

升级流程：

```bash
git pull
docker compose build
docker compose up -d
```

回滚：保留上一份镜像 tag，`docker compose up -d` 时切回旧 tag 即可。

---

## 2. Web 静态部署

### 2.1 前端

```bash
cd frontend
VITE_BUILD_TARGET=web npm run build      # 默认即 web
# dist/ 直接上传 CDN / nginx / S3+CloudFront
```

`nginx.conf`（仓库已含基础版）：

```nginx
location / {
  try_files $uri $uri/ /index.html;
}
location /api/ {
  proxy_pass http://backend:5001;
  proxy_set_header Host $host;
  proxy_set_header X-Real-IP $remote_addr;
}
```

### 2.2 后端

任意 Python 3.12 运行时即可。生产建议：

```bash
cd backend
.venv/bin/python -m gunicorn 'app:create_app()' \
  --workers 2 --threads 4 --bind 0.0.0.0:5001 \
  --access-logfile - --error-logfile -
```

K8s 部署：参考 `docker-compose.yml` 的 backend service，转成 Deployment + Service + 持久 PVC（DuckDB / kuzu_db / uploads）。

---

## 3. Tauri Desktop

### 3.1 一次性环境

```bash
# Rust toolchain
rustup default stable
# Tauri CLI
cargo install tauri-cli --version "^2.0"
# 前端依赖
cd frontend
npm install -D @tauri-apps/cli@^2.0 @tauri-apps/api@^2.0
# Windows: 安装 WebView2 runtime（系统级）
# Linux:  apt install libwebkit2gtk-4.1-dev build-essential curl wget file libssl-dev libgtk-3-dev libayatana-appindicator3-dev librsvg2-dev
# macOS:  xcode-select --install
```

### 3.2 开发

```bash
cd frontend
npx tauri dev
# 自动跑 npm run dev (Vite)，并把 webview 嵌进 Tauri 窗口
```

### 3.3 生产打包

```bash
cd frontend
VITE_BUILD_TARGET=tauri npm run build
npx tauri build
# 产物：src-tauri/target/release/bundle/{msi,nsis,deb,appimage,dmg}/
```

### 3.4 后端怎么办

桌面版有两种模式（按需选择，二选一即可）：

- **Sidecar 模式（推荐）**：`tauri.conf.json` 增 `bundle.externalBin = ["binaries/echolens-backend"]`，把 PyInstaller 打成独立可执行档随包发布，进程随窗口生命周期。
- **远端模式**：用户填写后端 URL，桌面只是 webview 壳。适合 SaaS。

当前 scaffold 走 **远端模式**（CSP 允许 `connect-src http://localhost:5001`），sidecar 留作 M6 工作。

### 3.5 已经就位的文件

```
frontend/src-tauri/
├── Cargo.toml
├── build.rs
├── tauri.conf.json
├── capabilities/default.json
├── src/main.rs
├── src/lib.rs
├── icons/.gitkeep            # 真实打包前需放图标
└── .gitignore                # target/, gen/
```

`Cargo.lock` / `target/` / `gen/` 已纳入根 `.gitignore`，不会污染仓库。

---

## 4. Capacitor Android

### 4.1 一次性环境

```bash
cd frontend
npm install -D @capacitor/cli @capacitor/core @capacitor/android
# 系统侧
# - Android Studio (含 Android SDK + Platform Tools)
# - Java 17+
# - 在 Android Studio 中安装至少一个 emulator image
```

### 4.2 首次初始化

```bash
cd frontend
VITE_BUILD_TARGET=capacitor npm run build
npx cap add android        # 生成 frontend/android/（已 .gitignore）
npx cap sync android
```

### 4.3 调试 / 打包

```bash
# 每次前端改动后
VITE_BUILD_TARGET=capacitor npm run build
npx cap sync android
npx cap open android       # → Android Studio 调试 / 出 APK / AAB
```

### 4.4 后端连接

Android emulator 内 `localhost` = emulator 本身，**不是 host**。本地开发把 `capacitor.config.ts` 临时改成：

```ts
server: {
  url: 'http://10.0.2.2:5001',   // emulator → host loopback
  cleartext: true,
}
```

真机调试用同网段 IP（`http://192.168.x.y:5001`）+ `cleartext: true`。生产必须 HTTPS + `cleartext: false`。

### 4.5 已经就位的文件

```
frontend/capacitor.config.ts        # appId / webDir / android 选项
```

`frontend/android/` 由 `npx cap add android` 生成，已纳入 `.gitignore`。

---

## 5. CI/CD 建议

| 路线 | CI 任务 |
|---|---|
| Docker Compose | `docker buildx build --push` 推到 GHCR / ECR；服务器 `docker compose pull && up -d` |
| Web 静态 | `npm run build` → 上传 dist/ 到 S3/OSS + invalidate CDN |
| Tauri Desktop | matrix: windows-latest / ubuntu-latest / macos-latest，跑 `tauri build`，artefact 上传到 GitHub Release |
| Capacitor Android | ubuntu-latest + Java 17，跑 `cap sync android` + `gradlew assembleRelease`，签名后传到 Play Console internal track |

后端 CI 已固化：`backend/.github/...` 待补，本里程碑外。

---

## 6. 风险与已知约束

- **CORS**：旧项目用 `*` 是已知问题；EchoLens 2.0 默认 `r"/api/*"` + `origins="*"` 仅供本地开发。生产部署务必把 origins 收窄到具体域名。
- **secrets**：`.env` 永不入 git；K8s 用 `Secret`，桌面 sidecar 用 OS keychain。
- **CSP**：Tauri `tauri.conf.json` 当前 `connect-src` 仅放行 `http://localhost:5001`，远端部署需要改成实际域名 / 走 IPC。
- **iOS**：本里程碑不纳入；后续若需要，加 `npx cap add ios` + Xcode toolchain + 证书。

---

## 7. 路线对照表

|  | Docker Compose | Web | Tauri Desktop | Capacitor Android |
|---|---|---|---|---|
| 终端用户安装难度 | 中（懂 Docker） | 低（开浏览器） | 低（exe / dmg） | 中（APK 或 Play） |
| 后端运行位置 | 同机 | 服务器 | sidecar / 远端 | 远端 |
| 离线可用 | 是 | 否 | sidecar 模式：是 | 否（需远端） |
| 当前状态 | ✅ 可用 | ✅ 可用 | 🛠 scaffold | 🛠 scaffold |
