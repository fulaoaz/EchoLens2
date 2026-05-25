# EchoLens 2.0 品牌指南

> **版本**: 1.0  
> **更新时间**: 2026-05-25

---

## 品牌概述

EchoLens 2.0 是一个电商舆情智能体仿真与数据预测决策平台。品牌标识体现了"回声"（Echo）和"透镜"（Lens）的核心概念，象征着数据的传播、聚焦和洞察。

---

## Logo 设计

### 设计理念

**核心元素**：

1. **同心圆波纹**：代表"Echo"（回声），象征舆情在社交媒体上的传播和扩散
2. **中心透镜**：代表"Lens"（透镜），象征数据的聚焦和分析
3. **流动线条**：代表数据流动和实时分析
4. **智能体节点**：代表多智能体仿真系统

**色彩寓意**：

- **紫蓝渐变**（外圈）：科技感、专业性、智能
- **青蓝渐变**（中心）：数据、洞察、清晰
- **绿色节点**：活力、增长、智能体

### Logo 变体

#### 1. 标准版（浅色背景）

**文件**：`logo.svg`

**使用场景**：
- 网站浅色主题
- 白色或浅色背景
- 打印材料（白纸）
- 演示文稿（浅色背景）

**最小尺寸**：32x32 像素

#### 2. 深色版（深色背景）

**文件**：`logo-dark.svg`

**使用场景**：
- 网站深色主题
- 黑色或深色背景
- 深色演示文稿
- 社交媒体深色模式

**最小尺寸**：32x32 像素

#### 3. Favicon（图标）

**文件**：`favicon.svg`

**使用场景**：
- 浏览器标签页图标
- 书签图标
- PWA 应用图标
- 移动应用图标

**尺寸**：16x16, 32x32, 48x48, 64x64 像素

### Logo 使用规范

#### ✅ 正确使用

- 保持 logo 周围有足够的留白空间（至少 logo 高度的 10%）
- 使用提供的官方文件，不要重新绘制
- 在浅色背景使用标准版，深色背景使用深色版
- 保持 logo 的纵横比，不要拉伸或压缩
- 确保 logo 清晰可见，不要放在复杂背景上

#### ❌ 错误使用

- 不要改变 logo 的颜色
- 不要旋转 logo
- 不要添加阴影、描边或其他效果
- 不要将 logo 放在低对比度的背景上
- 不要将 logo 与其他图形元素重叠
- 不要改变 logo 的比例

---

## 色彩系统

### 主色调

#### 紫蓝色（Primary）

```
Indigo 600: #4F46E5
Indigo 700: #4338CA
Purple 600: #7C3AED
Purple 700: #6D28D9
```

**用途**：
- 主要按钮
- 链接
- 重要标题
- 品牌强调

#### 青蓝色（Secondary）

```
Cyan 500: #06B6D4
Cyan 600: #0891B2
Blue 500: #3B82F6
Blue 600: #2563EB
```

**用途**：
- 次要按钮
- 图表主色
- 数据可视化
- 辅助元素

### 功能色

#### 成功（Success）

```
Green 500: #10B981
Green 600: #059669
```

**用途**：成功状态、正面数据、完成标记

#### 警告（Warning）

```
Yellow 500: #F59E0B
Yellow 600: #D97706
```

**用途**：警告信息、中等可靠性、注意事项

#### 错误（Error）

```
Red 500: #EF4444
Red 600: #DC2626
```

**用途**：错误状态、负面数据、危险操作

#### 信息（Info）

```
Blue 500: #3B82F6
Blue 600: #2563EB
```

**用途**：提示信息、帮助文本、中性通知

### 中性色

#### 浅色主题

```
Gray 50: #F9FAFB   (背景)
Gray 100: #F3F4F6  (次要背景)
Gray 200: #E5E7EB  (边框)
Gray 300: #D1D5DB  (分隔线)
Gray 400: #9CA3AF  (禁用文本)
Gray 500: #6B7280  (次要文本)
Gray 600: #4B5563  (主要文本)
Gray 900: #111827  (标题)
```

#### 深色主题

```
Gray 900: #111827  (背景)
Gray 800: #1F2937  (次要背景)
Gray 700: #374151  (边框)
Gray 600: #4B5563  (分隔线)
Gray 500: #6B7280  (禁用文本)
Gray 400: #9CA3AF  (次要文本)
Gray 300: #D1D5DB  (主要文本)
Gray 50: #F9FAFB   (标题)
```

---

## 字体系统

### 中文字体

**主字体**：系统默认无衬线字体

```css
font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 
             'Hiragino Sans GB', 'Microsoft YaHei', 'Helvetica Neue', 
             Helvetica, Arial, sans-serif;
```

**用途**：正文、界面文本、标题

### 英文字体

**主字体**：Inter / System Sans

```css
font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 
             Roboto, sans-serif;
```

**用途**：英文界面、数字、代码

### 等宽字体

**代码字体**：JetBrains Mono / Consolas

```css
font-family: 'JetBrains Mono', 'Fira Code', Consolas, 'Courier New', monospace;
```

**用途**：代码块、API 响应、日志

### 字体大小

```
xs:   12px / 0.75rem   (辅助文本)
sm:   14px / 0.875rem  (次要文本)
base: 16px / 1rem      (正文)
lg:   18px / 1.125rem  (强调文本)
xl:   20px / 1.25rem   (小标题)
2xl:  24px / 1.5rem    (中标题)
3xl:  30px / 1.875rem  (大标题)
4xl:  36px / 2.25rem   (主标题)
```

### 字重

```
Light:   300  (辅助文本)
Regular: 400  (正文)
Medium:  500  (强调)
Semibold: 600 (小标题)
Bold:    700  (标题)
```

---

## 图标系统

### 图标风格

- **风格**：线性图标（Outline）
- **粗细**：1.5px - 2px
- **圆角**：圆润（rounded）
- **尺寸**：16px, 20px, 24px, 32px

### 推荐图标库

- **Heroicons**（主要）
- **Lucide Icons**（备选）
- **Tabler Icons**（备选）

---

## 应用示例

### 网站

- **Favicon**：`favicon.svg` (32x32)
- **Header Logo**：`logo.svg` (高度 40-48px)
- **Footer Logo**：`logo.svg` (高度 32px)

### 桌面应用（Tauri）

- **窗口图标**：256x256, 128x128, 64x64, 32x32, 16x16
- **系统托盘图标**：32x32, 16x16

### 移动应用（Capacitor）

- **iOS App Icon**：1024x1024 (App Store), 180x180, 120x120, 87x87, 80x80, 76x76, 60x60, 58x58, 40x40, 29x29, 20x20
- **Android App Icon**：512x512 (Play Store), 192x192, 144x144, 96x96, 72x72, 48x48, 36x36

### 社交媒体

- **Twitter/X Card**：1200x630
- **Facebook Card**：1200x630
- **LinkedIn Card**：1200x627
- **微信分享**：500x400

### 文档

- **封面图**：1920x1080
- **缩略图**：400x300
- **头像**：200x200

---

## 品牌语调

### 核心价值观

- **专业**：提供可靠的数据分析和决策支持
- **创新**：采用前沿的 AI 和仿真技术
- **易用**：简洁直观的用户体验
- **开放**：开源、透明、社区驱动

### 语言风格

- **清晰**：使用简洁明了的语言，避免行话
- **友好**：保持专业的同时，语气亲切
- **准确**：数据和技术描述准确无误
- **积极**：强调解决方案和价值

### 文案示例

#### ✅ 推荐

- "让数据说话，让决策有据"
- "智能体仿真，预见未来"
- "从数据到洞察，一站式解决方案"

#### ❌ 避免

- "最强大的舆情分析工具"（过度夸张）
- "革命性的技术突破"（空洞宣传）
- "简单易用，人人都会"（过度简化）

---

## 文件清单

### Logo 文件

```
frontend/public/
├── logo.svg           # 标准版 logo（浅色背景）
├── logo-dark.svg      # 深色版 logo（深色背景）
└── favicon.svg        # Favicon 图标
```

### 图标文件（待生成）

```
frontend/public/icons/
├── icon-16x16.png
├── icon-32x32.png
├── icon-48x48.png
├── icon-64x64.png
├── icon-128x128.png
├── icon-192x192.png
├── icon-256x256.png
└── icon-512x512.png

frontend/src-tauri/icons/
├── icon.icns          # macOS
├── icon.ico           # Windows
├── icon.png           # Linux
└── [各种尺寸]

frontend/android/app/src/main/res/
└── [Android 图标资源]

frontend/ios/App/App/Assets.xcassets/
└── [iOS 图标资源]
```

---

## 更新日志

### 1.0 (2026-05-25)
- 初始版本发布
- 创建标准版和深色版 logo
- 创建 favicon
- 定义色彩系统
- 定义字体系统
- 定义使用规范

---

## 联系方式

如有品牌使用相关问题，请联系：

- **邮件**：brand@echolens.ai
- **GitHub**：https://github.com/yourusername/echolens

---

**版权所有 © 2026 EchoLens Team**  
**许可证**: AGPL-3.0
