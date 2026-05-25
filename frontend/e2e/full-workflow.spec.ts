import { test, expect } from '@playwright/test'

/**
 * 端到端冒烟测试 - 完整业务链路
 *
 * 覆盖：新建项目 → 材料采集 → seed report → 仿真/预测 → 决策 → 报告下载
 *
 * 验证点：
 * 1. 决策看板 chip 颜色与下载 HTML/PDF 中的 reliability tier 一致
 * 2. 每条结论都能通过 Run chip 回到原始 run
 * 3. reliability tier 的三档颜色（强/一般/弱）正确显示
 */

test.describe('EchoLens 完整业务链路', () => {
  test.beforeEach(async ({ page }) => {
    // 导航到首页
    await page.goto('/')
    await expect(page).toHaveTitle(/EchoLens/)
  })

  test('完整工作流：项目创建 → 采集 → 仿真 → 决策 → 报告', async ({ page }) => {
    // ========== 步骤 1：新建项目 ==========
    await test.step('新建项目', async () => {
      // 点击"新建项目"按钮
      await page.click('button:has-text("新建项目")')

      // 填写项目信息
      await page.fill('input[placeholder*="项目名称"]', 'E2E测试项目')
      await page.fill('textarea[placeholder*="描述"]', '端到端冒烟测试')

      // 提交
      await page.click('button:has-text("创建")')

      // 等待项目创建成功并跳转到项目详情页
      await page.waitForURL(/\/project\/\d+/)
      await expect(page.locator('h1')).toContainText('E2E测试项目')
    })

    // ========== 步骤 2：材料采集 ==========
    await test.step('上传材料并构建知识图谱', async () => {
      // 点击"材料采集"标签
      await page.click('text=材料采集')

      // 上传测试文件（假设有测试数据）
      const fileInput = page.locator('input[type="file"]')
      await fileInput.setInputFiles('./e2e/fixtures/test-document.txt')

      // 等待上传完成
      await expect(page.locator('text=上传成功')).toBeVisible({ timeout: 30000 })

      // 点击"构建图谱"
      await page.click('button:has-text("构建图谱")')

      // 等待图谱构建完成
      await expect(page.locator('text=图谱构建完成')).toBeVisible({ timeout: 60000 })
    })

    // ========== 步骤 3：配置并运行仿真 ==========
    await test.step('配置并运行仿真', async () => {
      // 点击"仿真配置"标签
      await page.click('text=仿真配置')

      // 选择实体（至少选择一个）
      await page.click('input[type="checkbox"]').first()

      // 配置仿真参数
      await page.fill('input[placeholder*="轮数"]', '10')

      // 启动仿真
      await page.click('button:has-text("启动仿真")')

      // 等待仿真完成
      await expect(page.locator('text=仿真完成')).toBeVisible({ timeout: 120000 })
    })

    // ========== 步骤 4：查看决策看板并验证 reliability tier ==========
    let reliabilityValue: number | null = null
    let reliabilityTierSlug: string | null = null

    await test.step('查看决策看板并记录 reliability tier', async () => {
      // 点击"决策看板"标签
      await page.click('text=决策看板')

      // 等待决策数据加载
      await page.waitForSelector('.decision-card', { timeout: 30000 })

      // 获取第一个决策的 reliability 值和 tier
      const firstDecision = page.locator('.decision-card').first()

      // 获取 reliability 数值
      const reliabilityText = await firstDecision.locator('.reliability-value').textContent()
      reliabilityValue = reliabilityText ? parseFloat(reliabilityText) : null

      // 获取 chip 的颜色类型（通过 class 或 data-type）
      const reliabilityChip = firstDecision.locator('.reliability-chip')
      const chipType = await reliabilityChip.getAttribute('data-type')

      // 根据阈值验证 chip 类型
      if (reliabilityValue !== null) {
        if (reliabilityValue >= 0.7) {
          expect(chipType).toBe('success') // 强
          reliabilityTierSlug = 'strong'
        } else if (reliabilityValue >= 0.4) {
          expect(chipType).toBe('warning') // 一般
          reliabilityTierSlug = 'fair'
        } else {
          expect(chipType).toBe('error') // 弱
          reliabilityTierSlug = 'weak'
        }
      }
    })

    // ========== 步骤 5：点击 Run chip 验证 highlight ==========
    await test.step('点击 Run chip 验证原始 run highlight', async () => {
      // 点击第一个 Run chip
      const firstRunChip = page.locator('.run-chip').first()
      await firstRunChip.click()

      // 验证对应的 run 被 highlight（例如添加了特定 class）
      await expect(page.locator('.run-item.highlighted')).toBeVisible()

      // 验证可以看到 run 的详细信息
      await expect(page.locator('.run-detail-panel')).toBeVisible()
    })

    // ========== 步骤 6：生成并下载报告 ==========
    await test.step('生成并下载报告', async () => {
      // 点击"报告"标签
      await page.click('text=报告')

      // 点击"生成报告"
      await page.click('button:has-text("生成报告")')

      // 等待报告生成完成
      await expect(page.locator('text=报告生成完成')).toBeVisible({ timeout: 60000 })

      // 下载 HTML 报告
      const downloadPromise = page.waitForEvent('download')
      await page.click('button:has-text("下载 HTML")')
      const download = await downloadPromise

      // 保存下载的文件
      const downloadPath = `./e2e/downloads/${download.suggestedFilename()}`
      await download.saveAs(downloadPath)

      // 验证下载的 HTML 文件存在
      const fs = require('fs')
      expect(fs.existsSync(downloadPath)).toBeTruthy()
    })

    // ========== 步骤 7：验证下载的 HTML 中 reliability tier 一致 ==========
    await test.step('验证下载 HTML 中的 reliability tier 与看板一致', async () => {
      const fs = require('fs')
      const downloadPath = `./e2e/downloads/report.html` // 假设文件名

      // 读取 HTML 内容
      const htmlContent = fs.readFileSync(downloadPath, 'utf-8')

      // 验证 HTML 中包含正确的 reliability tier class
      if (reliabilityTierSlug) {
        expect(htmlContent).toContain(`metric-reliability-${reliabilityTierSlug}`)
      }

      // 验证 HTML 中的 reliability 数值与看板一致
      if (reliabilityValue !== null) {
        const reliabilityRegex = new RegExp(`reliability[^>]*>${reliabilityValue.toFixed(2)}`)
        expect(htmlContent).toMatch(reliabilityRegex)
      }
    })
  })

  test('验证 reliability tier 边界值', async ({ page }) => {
    // 这个测试用于验证三个阈值边界的颜色是否正确
    // 需要准备三个不同 reliability 值的测试数据

    await test.step('验证强证据 (>=0.7) 显示 success 绿色', async () => {
      // 导航到有 reliability=0.7 或更高的决策
      await page.goto('/project/1/decisions?reliability=0.7')

      const chip = page.locator('.reliability-chip').first()
      await expect(chip).toHaveAttribute('data-type', 'success')
    })

    await test.step('验证一般证据 (>=0.4, <0.7) 显示 warning 黄色', async () => {
      // 导航到有 reliability=0.4-0.69 的决策
      await page.goto('/project/1/decisions?reliability=0.5')

      const chip = page.locator('.reliability-chip').first()
      await expect(chip).toHaveAttribute('data-type', 'warning')
    })

    await test.step('验证弱证据 (<0.4) 显示 error 红色', async () => {
      // 导航到有 reliability<0.4 的决策
      await page.goto('/project/1/decisions?reliability=0.3')

      const chip = page.locator('.reliability-chip').first()
      await expect(chip).toHaveAttribute('data-type', 'error')
    })
  })
})
