# EchoLens 2.0 开发进度报告

> **更新时间**: 2026-05-25  
> **当前阶段**: Phase E 已完成

---

## 项目概述

EchoLens 2.0 是一个电商舆情智能体仿真 + 数据预测决策平台，面向三创赛电子商务大数据分析赛道。

**核心能力**：
- 上传商品方案 → 真实多平台爬取
- 双轨分析：多智能体仿真 / 时序+因果预测
- 综合决策看板 + 自包含 HTML 报告

---

## 架构总览

```
前端 (Vue 3 + Naive UI)
    ↓ axios + SSE
后端 (Flask + Pydantic 2)
    ├─ crawler (多平台爬虫)
    ├─ simulator (OASIS 仿真)
    ├─ predictor (时序+因果预测)
    ├─ kg (Kuzu + LightRAG + NetworkX)
    └─ dashboard (决策综合)
    ↓
DuckDB / Parquet + 外部 LLM API
```

---

## 开发阶段完成情况

### Phase A — 架构脱钩 ✅
- 后端 Flask 3 + Pydantic 2 脚手架
- 前端 Vue 3.5 + Vite 7 + Naive UI
- DuckDB 本地存储
- Docker Compose 部署配置

### Phase B — 真实采集闭环 ✅
- 多平台爬虫引擎（京东、淘宝、微博、小红书）
- 合规性检查（robots.txt + 频率限制）
- 数据清洗管道（去重、对齐、清洗）
- Seed Report 生成

### Phase C — 自有检索与图谱 ✅
- Kuzu 图数据库集成
- LightRAG 知识图谱引擎
- 本体生成器（LLM 驱动）
- 图谱搜索与同步

### Phase D — 仿真/预测/决策 ✅
- OASIS 社交媒体仿真框架集成
- 时序预测（ARIMA + Prophet）
- 因果推断（DoWhy）
- 决策引擎（多维度综合评分）

### Phase E — 报告与前端整合 ✅

#### 1. 报告层 ✅
- Evidence report 生成
- 自包含 HTML 下载（内联 CSS）
- 最弱链 reliability 等级标签（强/一般/弱）
- 三档颜色映射（绿/黄/红）

#### 2. 前端整合 ✅
- 项目详情页串起全部业务链路
- 决策看板 chip a11y（role="button" + aria-label + Enter/Space）
- Run 反查 highlight（点击 Run chip 高亮原始 run）

#### 3. Reliability Tier 共享模块 ✅ (任务 #55)
**问题**：阈值在四处重复书写，容易不一致
- 后端 markdown 字面
- 后端 HTML slug + CSS
- 前端 chip 着色

**解决方案**：
- 后端共享模块：`backend/app/services/reliability_tier.py`
  - 单一权威阈值：`STRONG_THRESHOLD=0.7` / `FAIR_THRESHOLD=0.4`
  - `tier_for(value)` 返回 `(label_zh, slug)`
- 前端 composable：`frontend/src/composables/useReliabilityTier.ts`
  - 镜像后端阈值和分类逻辑
  - 返回 `{ label, slug, naiveType }` 用于 Naive UI
- 双端契约测试：
  - 后端：`backend/tests/test_reliability_tier.py` (36 passed)
  - 前端：`frontend/src/composables/__tests__/useReliabilityTier.spec.ts` (27 passed)
  - 相同边界样本 → 相同 tier
  - 任意一端改阈值会同时打破两端测试

**验证结果**：
- 后端测试：246 passed, 1 skipped
- 前端 lint：0 warnings
- 前端测试：27 passed
- 前端构建：成功

#### 4. E2E 测试框架 ✅ (任务 #56)
**目标**：端到端冒烟测试覆盖完整业务链路

**实现**：
- 安装并配置 Playwright
- 配置文件：`frontend/playwright.config.ts`
- 基础冒烟测试：`frontend/e2e/smoke.spec.ts`
  - 应用启动和导航
  - Reliability tier 视觉一致性验证
  - 前后端契约测试（需要后端服务）
- 完整工作流测试：`frontend/e2e/full-workflow.spec.ts`
  - 新建项目 → 材料采集 → seed report
  - 仿真/预测 → 决策（点 Run chip 验证 highlight + tier 颜色）
  - 报告 + HTML 下载
  - 验证每条结论都能回到原始 run
- 测试数据：`frontend/e2e/fixtures/test-document.txt`
- 文档：`frontend/e2e/README.md`
- npm 脚本：
  - `npm run test:e2e` - 运行所有 E2E 测试
  - `npm run test:e2e:ui` - UI 模式（推荐调试）
  - `npm run test:e2e:debug` - Debug 模式

**浏览器安装**：
- Chromium 1223 (Chrome for Testing 148.0.7778.96)
- Chrome Headless Shell 1223

---

## 测试覆盖

### 后端测试
- **总计**：246 passed, 1 skipped
- **覆盖模块**：
  - API 层：crawler, decision, prediction, projects, report, simulation
  - 服务层：crawler_engine, kg_search, predictor, simulator_runner
  - 数据层：project_store, duckdb
  - 新增：reliability_tier (36 tests)

### 前端测试
- **单元测试**：27 passed (useReliabilityTier)
- **组件测试**：KpiCard, DecisionBoardPanel a11y
- **E2E 测试**：Playwright 框架已搭建

### 代码质量
- **后端**：pytest + mypy
- **前端**：ESLint + Prettier (0 warnings)
- **构建**：前后端构建均通过

---

## 技术栈

### 后端
- **框架**：Flask 3 + Pydantic 2
- **数据库**：DuckDB (本地) + Kuzu (图数据库)
- **知识图谱**：LightRAG + NetworkX
- **仿真**：OASIS (CAMEL-AI)
- **预测**：statsmodels (ARIMA) + Prophet + DoWhy
- **测试**：pytest + pytest-asyncio

### 前端
- **框架**：Vue 3.5 + Vite 7
- **UI 库**：Naive UI
- **状态管理**：Pinia
- **图表**：ECharts + D3.js + @antv/g6
- **测试**：Vitest + Playwright
- **类型检查**：TypeScript 5.6

### DevOps
- **容器化**：Docker + Docker Compose
- **CI/CD**：GitHub Actions
- **代码质量**：ESLint + Prettier + mypy

---

## 下一步计划

### Phase F（候选）
1. **性能优化**
   - 前端懒加载和代码分割
   - 后端异步任务队列优化
   - 数据库查询优化

2. **用户体验增强**
   - 实时进度推送（SSE）
   - 离线模式支持
   - 移动端适配

3. **功能扩展**
   - 更多平台爬虫适配器
   - 更多预测模型集成
   - 自定义决策规则

4. **文档完善**
   - API 文档（OpenAPI）
   - 用户手册
   - 开发者指南

---

## 快速开始

### 本地开发

```bash
# 后端
cd backend
uv venv .venv
uv pip install --python .venv/Scripts/python.exe -e ".[dev]"
.venv/Scripts/python -m pytest -q
.venv/Scripts/python run.py   # → http://localhost:5001

# 前端
cd frontend
npm install
npm run test                   # 单元测试
npm run test:e2e:ui            # E2E 测试（需要后端运行）
npm run dev                    # → http://localhost:3000
```

### Docker 部署

```bash
docker compose up
```

---

## 贡献指南

### 提交规范

遵循 Conventional Commits：
- `feat:` 新功能
- `fix:` Bug 修复
- `docs:` 文档更新
- `test:` 测试相关
- `refactor:` 重构
- `perf:` 性能优化
- `chore:` 构建/工具链

### 测试要求

- 新功能必须包含单元测试
- 关键路径需要 E2E 测试
- 所有测试必须通过才能合并

### 代码审查

- 后端：pytest 全绿 + mypy 无错误
- 前端：ESLint 0 warnings + 构建成功
- E2E：关键路径测试通过

---

## 许可证

AGPL-3.0

---

## 联系方式

- **项目仓库**：F:\Projects\EchoLens2
- **文档**：docs/
- **问题反馈**：GitHub Issues

---

**最后更新**：2026-05-25  
**版本**：2.0.0-alpha  
**状态**：Phase E 已完成，进入 Phase F 规划阶段
