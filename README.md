# EchoLens 2.0

> **电商舆情智能体 + 数据预测决策平台** · 面向三创赛电子商务大数据分析赛道
>
> 一句话：上传商品方案 → 真实多平台爬取 → 双轨分析（多智能体仿真 / 时序+因果预测） → 综合决策看板

## 项目状态

🚧 M0 阶段（脚手架）已完成。M1 起进入实现阶段。详见 [`../EchoLens/.omc/plans/echolens-v2-prd.md`](../EchoLens/.omc/plans/echolens-v2-prd.md)。

## 架构总览

```
┌──── Vue 3 + Naive UI 前端（3000）────┐
│  工作台 / 项目详情 / 仿真 / 预测 / 决策 │
└──────────────┬───────────────────────┘
               │ axios + SSE
┌──────────────▼───────────────────────┐
│  Flask + Pydantic 2 后端（5001）       │
│  crawler · simulator · predictor      │
│  kg(Kuzu+LightRAG+NetworkX) · dashboard │
└──────────────┬───────────────────────┘
               │
       ┌───────┴────────┐
       ▼                ▼
   DuckDB / Parquet  外部 LLM API
```

## 快速开始

```bash
# 后端
cd backend
uv venv .venv
uv pip install --python .venv/Scripts/python.exe -e ".[dev]"
.venv/Scripts/python -m pytest -q
.venv/Scripts/python run.py   # → http://localhost:5001/health

# 前端
cd frontend
npm install
npm run dev                   # → http://localhost:3000
```

或一条命令：

```bash
docker compose up
```

## 目录

- `backend/` — Flask 3 + Pydantic 2 后端
- `frontend/` — Vue 3.5 + Vite 7 + Naive UI 前端
- `docs/` — 设计文档、技术 spike 报告
- `.github/workflows/` — CI

## 许可证

AGPL-3.0
