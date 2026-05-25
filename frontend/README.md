# EchoLens 2.0 · Frontend

Vue 3 + Vite 7 + TypeScript (strict) + Naive UI + Pinia.

## 开发

```bash
npm install
npm run dev          # http://localhost:3000  (proxy /api → http://localhost:5001)
```

## 构建

```bash
npm run lint
npm run type-check
npm run test
npm run build        # 输出 dist/
npm run preview
```

## 模块组织

- `src/api/` — axios 客户端 + 各业务域接口
- `src/components/{common,crawler,simulation,prediction,dashboard}/` — 业务组件
- `src/views/` — 路由视图（Workbench、ProjectDetail、SimulationConsole、PredictionLab、DecisionBoard）
- `src/stores/` — Pinia stores
- `src/styles/tokens.css` + `src/styles/naive-theme.ts` — 设计令牌与 Naive UI 主题覆盖
- `src/router/` — 路由

## Docker

```bash
docker build -t echolens2-frontend .
docker run -p 8080:80 echolens2-frontend
```

详见 PRD: `../docs` 与 `F:/Projects/EchoLens/.omc/plans/echolens-v2-prd.md`。
