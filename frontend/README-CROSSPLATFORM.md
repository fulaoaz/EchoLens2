# EchoLens 2.0 跨平台支持

EchoLens 2.0 支持多平台部署：Web、桌面端（Tauri）、移动端（Capacitor）。

## 平台支持矩阵

| 平台 | 状态 | 技术栈 | 构建命令 |
|------|------|--------|----------|
| Web | ✅ 完整支持 | Vue 3 + Vite | `npm run build` |
| Windows 桌面 | ✅ 完整支持 | Tauri 2.0 | `npm run tauri:build` |
| macOS 桌面 | ✅ 完整支持 | Tauri 2.0 | `npm run tauri:build` |
| Linux 桌面 | ✅ 完整支持 | Tauri 2.0 | `npm run tauri:build` |
| iOS | ✅ 完整支持 | Capacitor 8 | `npm run cap:run:ios` |
| Android | ✅ 完整支持 | Capacitor 8 | `npm run cap:run:android` |

## 架构设计

### 平台抽象层

`src/composables/usePlatform.ts` 提供统一的跨平台 API：

```typescript
// 平台检测
const { currentPlatform, isWeb, isTauri, isMobile } = usePlatform()

// 文件选择（自动适配平台）
const files = await pickFiles({ multiple: true, accept: '.pdf,.txt' })

// 网络请求（自动配置正确的 baseURL）
const apiUrl = getApiBaseUrl()

// 系统通知
await showNotification('标题', '内容')

// 平台能力检测
const capabilities = getPlatformCapabilities()
```

### 平台特定功能

#### Tauri 桌面端 (`src/composables/useTauri.ts`)

```typescript
// 窗口管理
const { minimize, toggleMaximize, close } = useWindow()

// 系统托盘
const { showWindow, hideWindow } = useTray()

// 应用信息
const { name, version } = useAppInfo()
```

#### 移动端适配 (`src/styles/mobile.css`)

- 响应式布局（< 768px 自动切换）
- 触摸友好的按钮尺寸（最小 44px）
- 安全区域适配（刘海屏）
- 横屏模式优化

## 开发指南

### 本地开发

```bash
# Web 开发
npm run dev

# Tauri 桌面开发（需要 Rust 环境）
npm run tauri:dev

# Capacitor 移动开发
npm run cap:sync
npm run cap:open:ios      # 打开 Xcode
npm run cap:open:android  # 打开 Android Studio
```

### 构建发布

```bash
# Web 构建
npm run build

# Tauri 桌面构建
npm run tauri:build        # 生产构建
npm run tauri:build:debug  # 调试构建

# Capacitor 移动构建
npm run cap:sync           # 同步 Web 资源到原生项目
npm run cap:run:ios        # 运行 iOS 应用
npm run cap:run:android    # 运行 Android 应用
```

## 平台差异处理

### API 基础 URL

- **Web**: 相对路径 `/api` 或环境变量 `VITE_API_BASE_URL`
- **Tauri**: `http://localhost:5001`
- **iOS 模拟器**: `http://localhost:5001`
- **Android 模拟器**: `http://10.0.2.2:5001`

### 文件访问

- **Web**: 使用 `<input type="file">` 选择器
- **Tauri**: 使用 `@tauri-apps/plugin-dialog` 原生对话框
- **Capacitor**: 使用 Capacitor Filesystem API

### 通知

- **Web**: 浏览器 Notification API
- **Tauri**: `@tauri-apps/plugin-notification` 原生通知
- **Capacitor**: `@capacitor/local-notifications` 本地通知

## 环境要求

### Tauri 桌面端

- **Rust**: >= 1.70
- **Node.js**: >= 18
- **Windows**: WebView2 Runtime
- **macOS**: macOS 10.15+
- **Linux**: webkit2gtk, libayatana-appindicator

安装 Rust：
```bash
# Windows
winget install Rustlang.Rustup

# macOS/Linux
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

### Capacitor 移动端

- **Node.js**: >= 18
- **iOS**: Xcode 14+, CocoaPods
- **Android**: Android Studio, JDK 17+

## 测试

```bash
# 单元测试
npm run test

# E2E 测试（需要后端运行）
npm run test:e2e

# 类型检查
npm run type-check

# 代码检查
npm run lint
```

## 已知限制

1. **Tauri 全局快捷键**: 需要额外安装 `@tauri-apps/plugin-global-shortcut`
2. **Capacitor 文件选择**: 部分平台需要额外权限配置
3. **移动端图表**: 大数据量图表可能需要性能优化

## 故障排查

### Tauri 构建失败

1. 确认 Rust 已安装：`rustc --version`
2. 更新 Rust：`rustup update`
3. 清理缓存：`cargo clean`

### Capacitor 同步失败

1. 确认已构建 Web 资源：`npm run build`
2. 清理原生项目：删除 `ios/` 和 `android/` 目录后重新 `cap add`
3. 检查 `capacitor.config.ts` 配置

### 移动端网络请求失败

1. 确认后端服务运行在正确端口（5001）
2. Android 模拟器使用 `10.0.2.2` 而非 `localhost`
3. iOS 需要在 `Info.plist` 中配置 App Transport Security

## 参考资料

- [Tauri 官方文档](https://tauri.app/)
- [Capacitor 官方文档](https://capacitorjs.com/)
- [Vue 3 文档](https://vuejs.org/)
- [Naive UI 文档](https://www.naiveui.com/)
