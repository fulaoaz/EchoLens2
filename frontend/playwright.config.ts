import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright E2E 测试配置
 *
 * 端到端冒烟测试覆盖完整业务链路：
 * 新建项目 → 材料采集 → seed report → 仿真/预测 → 决策 → 报告下载
 */
export default defineConfig({
  testDir: './e2e',

  // 最长测试时间（完整链路可能需要较长时间）
  timeout: 5 * 60 * 1000, // 5 minutes

  // 每个测试的 expect 超时
  expect: {
    timeout: 10000,
  },

  // 失败时重试次数
  fullyParallel: false,
  retries: process.env.CI ? 2 : 0,

  // CI 环境下并行 worker 数量
  workers: process.env.CI ? 1 : 1,

  // 测试报告
  reporter: [['html', { outputFolder: 'playwright-report' }], ['list']],

  use: {
    // 基础 URL（假设前端运行在 5173，后端在 5000）
    baseURL: 'http://localhost:5173',

    // 截图和视频
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    trace: 'retain-on-failure',

    // 浏览器上下文选项
    viewport: { width: 1920, height: 1080 },
    ignoreHTTPSErrors: true,
  },

  // 测试前启动服务
  webServer: [
    {
      command: 'npm run dev',
      url: 'http://localhost:5173',
      reuseExistingServer: !process.env.CI,
      timeout: 120000,
    },
  ],

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
})
