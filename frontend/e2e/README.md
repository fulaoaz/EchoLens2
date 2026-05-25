# EchoLens E2E 测试

端到端测试使用 Playwright 框架，覆盖完整业务链路。

## 测试覆盖

### 1. 基础冒烟测试 (`smoke.spec.ts`)

- 应用启动和基本导航
- Reliability tier 视觉一致性验证
- 前后端契约测试（需要后端服务）

### 2. 完整工作流测试 (`full-workflow.spec.ts`)

完整业务链路：
1. 新建项目
2. 材料采集（上传文档 + 构建知识图谱）
3. 配置并运行仿真
4. 查看决策看板
5. 验证 Run chip highlight
6. 生成并下载报告
7. 验证报告中的 reliability tier 与看板一致

## 运行测试

### 前置条件

```bash
# 安装依赖
npm install

# 安装 Playwright 浏览器
npx playwright install chromium
```

### 运行测试

```bash
# 运行所有 E2E 测试
npm run test:e2e

# 使用 UI 模式运行（推荐用于调试）
npm run test:e2e:ui

# Debug 模式（逐步执行）
npm run test:e2e:debug

# 运行特定测试文件
npx playwright test e2e/smoke.spec.ts

# 运行特定测试用例
npx playwright test -g "应用可以正常启动"
```

### 查看测试报告

```bash
# 生成并打开 HTML 报告
npx playwright show-report
```

## 测试配置

配置文件：`playwright.config.ts`

关键配置：
- **baseURL**: `http://localhost:5173` (前端开发服务器)
- **timeout**: 5 分钟（完整链路测试可能需要较长时间）
- **webServer**: 自动启动前端开发服务器
- **screenshot/video**: 失败时自动截图和录屏

## Reliability Tier 契约测试

### 测试目标

确保决策看板 chip 颜色与下载 HTML/PDF 中的 reliability tier 视觉一致。

### 阈值定义

- **强证据** (`strong`): reliability >= 0.7 → `success` (绿色)
- **一般证据** (`fair`): 0.4 <= reliability < 0.7 → `warning` (黄色)
- **弱证据** (`weak`): reliability < 0.4 → `error` (红色)
- **未知** (`unknown`): null/undefined → `default` (灰色)

### 验证点

1. **前端 composable 阈值**: `useReliabilityTier.ts` 中的 `STRONG_THRESHOLD=0.7` / `FAIR_THRESHOLD=0.4`
2. **Chip 颜色映射**: 边界值 (0.39, 0.4, 0.69, 0.7) 的颜色正确
3. **后端一致性**: 前后端对相同样本返回相同 tier (需要后端服务)
4. **HTML 报告一致性**: 下载的 HTML 中 `metric-reliability-{slug}` 类名与看板一致

## 测试数据

测试 fixture 位于 `e2e/fixtures/`:
- `test-document.txt`: 用于材料采集的示例文档

下载的报告保存在 `e2e/downloads/` (已加入 .gitignore)

## CI/CD 集成

```yaml
# GitHub Actions 示例
- name: Install Playwright
  run: npx playwright install --with-deps chromium

- name: Run E2E tests
  run: npm run test:e2e

- name: Upload test results
  if: always()
  uses: actions/upload-artifact@v3
  with:
    name: playwright-report
    path: playwright-report/
```

## 故障排查

### 测试超时

如果测试超时，检查：
1. 后端服务是否正常运行 (http://localhost:5000)
2. 前端开发服务器是否正常启动 (http://localhost:5173)
3. 网络连接是否正常

### 元素未找到

如果测试找不到元素，可能是：
1. 选择器不正确（检查实际 DOM 结构）
2. 页面加载未完成（增加 `waitForSelector` 超时）
3. 组件渲染条件未满足（检查数据是否正确加载）

### 截图和视频

失败的测试会自动生成截图和视频，位于 `test-results/` 目录。

## 开发建议

1. **先写基础测试**: 从简单的导航和元素存在性测试开始
2. **使用 UI 模式**: `npm run test:e2e:ui` 可以实时查看测试执行
3. **善用 debug 模式**: `npm run test:e2e:debug` 可以逐步调试
4. **保持测试独立**: 每个测试应该能独立运行，不依赖其他测试的状态
5. **使用 test.step**: 将复杂测试分解为多个步骤，便于定位问题

## 参考资料

- [Playwright 官方文档](https://playwright.dev/)
- [Playwright Best Practices](https://playwright.dev/docs/best-practices)
- [Vue Testing Handbook](https://lmiller1990.github.io/vue-testing-handbook/)
