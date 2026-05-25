# EchoLens 2.0

<div align="center">

**E-commerce Sentiment Agent Simulation + Data Prediction & Decision Platform**

[![Version](https://img.shields.io/badge/version-2.0.0--rc1-blue.svg)](https://github.com/zuohenlin/EchoLens2)
[![License](https://img.shields.io/badge/license-AGPL--3.0-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Vue](https://img.shields.io/badge/vue-3.5-green.svg)](https://vuejs.org/)

English | [简体中文](README.md)

</div>

---

## 📖 Introduction

EchoLens 2.0 is an intelligent decision platform for e-commerce sentiment analysis, helping businesses and researchers:

- 📊 **Real Data Collection**: Automatically collect product and sentiment data from JD, Taobao, Weibo, Xiaohongshu, and more
- 🤖 **Agent Simulation**: Simulate millions of users' social media behavior using the OASIS framework
- 📈 **Predictive Analysis**: Predict product sales and sentiment trends based on time series forecasting and causal inference
- 🎯 **Decision Support**: Generate traceable decision recommendations by synthesizing multi-dimensional data
- 📄 **Analysis Reports**: Automatically generate professional analysis reports with complete evidence chains

**One-sentence workflow**: Upload product plan → Real multi-platform crawling → Dual-track analysis (multi-agent simulation / time series + causal prediction) → Comprehensive decision dashboard → Generate report

---

## ✨ Core Features

### 🔍 Multi-Platform Data Collection
- Support for mainstream platforms: JD, Taobao, Weibo, Xiaohongshu
- Automatic data cleaning and deduplication
- Compliance with robots.txt and rate limiting

### 🧠 Knowledge Graph Construction
- Automatic entity and relationship extraction
- Visual graph display
- Support for graph search and queries

### 🎭 Agent Simulation
- Social media simulation based on OASIS framework
- Support for million-scale agents
- Multi-round iterative sentiment propagation simulation

### 📊 Predictive Analysis
- Time series forecasting (ARIMA, Prophet)
- Causal inference (DoWhy)
- Trend analysis and visualization

### 🎯 Decision Dashboard
- Multi-dimensional comprehensive scoring
- Evidence chain tracing
- Reliability level annotation

### 📄 Report Generation
- Self-contained HTML reports
- Support for PDF and Markdown export
- Complete evidence chains included

---

## 🚀 Quick Start

### Prerequisites

- **Python**: ≥ 3.11
- **Node.js**: ≥ 18
- **Docker**: ≥ 20.10 (optional)

### Local Development

#### 1. Clone Repository

```bash
git clone https://github.com/zuohenlin/EchoLens2.git
cd echolens
```

#### 2. Configure Environment Variables

```bash
cp .env.example .env
# Edit .env file and fill in necessary API keys
```

#### 3. Start Backend

```bash
cd backend
uv venv .venv
uv pip install --python .venv/Scripts/python.exe -e ".[dev]"
.venv/Scripts/python run.py   # → http://localhost:5001
```

#### 4. Start Frontend

```bash
cd frontend
npm install
npm run dev                   # → http://localhost:3000
```

### Docker Deployment

```bash
docker compose up
```

Visit http://localhost:3000 to start using.

For detailed deployment guide, see [DEPLOYMENT.md](DEPLOYMENT.md).

---

## 📚 Documentation

- [User Manual](docs/USER_MANUAL.md) - Complete usage guide (Chinese)
- [API Documentation](docs/API.md) - RESTful API reference (Chinese)
- [Development Progress](PROGRESS.md) - Project development progress and tech stack (Chinese)
- [Deployment Guide](DEPLOYMENT.md) - Production environment deployment guide (Chinese)
- [Contributing Guide](CONTRIBUTING.md) - How to contribute (Chinese)

---

## 🏗️ Project Status

**Current Version**: `2.0.0-rc1` (Release Candidate)  
**Release Date**: 2026-05-25  
**Next Version**: `2.0.0` (Stable)

### ✅ Completed Features

- ✅ **Multi-platform Data Collection**: Automated crawling from JD, Taobao, Weibo, Xiaohongshu
- ✅ **Knowledge Graph**: Automated graph generation with Kuzu + LightRAG
- ✅ **Agent Simulation**: OASIS framework supporting million-scale social media simulation
- ✅ **Predictive Analytics**: Time series (ARIMA, Prophet) + causal inference (DoWhy)
- ✅ **Decision Dashboard**: Multi-dimensional scoring + evidence chain tracing + run highlighting
- ✅ **Report Generation**: Auto-generate HTML/PDF/Markdown/JSON reports
- ✅ **Cross-platform**: Web, Desktop (Tauri), Mobile (Capacitor)
- ✅ **Internationalization**: Chinese and English support
- ✅ **Complete Documentation**: User manual, API docs, contributing guide, security policy

### 🚀 Planned Features

- 🔄 **Real-time Monitoring**: WebSocket push + real-time alerts
- 🔄 **Custom Models**: Support user-uploaded prediction models
- 🔄 **Collaboration**: Multi-user collaboration + permission management
- 🔄 **Data Export**: More formats (Excel, CSV, Parquet)
- 🔄 **API Extensions**: GraphQL API + Webhook integration

---

## 🏛️ Architecture Overview

```
┌──────────────────────────────────────┐
│    Vue 3 + Naive UI Frontend (3000)   │
│  Workbench / Projects / Sim / Pred    │
└──────────────┬───────────────────────┘
               │ axios + SSE
┌──────────────▼───────────────────────┐
│   Flask + Pydantic 2 Backend (5001)   │
│  ┌────────────────────────────────┐  │
│  │ crawler  - Multi-platform data  │  │
│  │ simulator - OASIS agent sim     │  │
│  │ predictor - Time series + causal│  │
│  │ kg - Kuzu+LightRAG+NetworkX     │  │
│  │ dashboard - Decision synthesis  │  │
│  └────────────────────────────────┘  │
└──────────────┬───────────────────────┘
               │
       ┌───────┴────────┐
       ▼                ▼
   DuckDB / Parquet  External LLM API
```

---

## 🛠️ Tech Stack

### Backend
- **Framework**: Flask 3 + Pydantic 2
- **Database**: DuckDB (local) + Kuzu (graph database)
- **Knowledge Graph**: LightRAG + NetworkX
- **Simulation**: OASIS (CAMEL-AI)
- **Prediction**: statsmodels (ARIMA) + Prophet + DoWhy
- **Testing**: pytest + pytest-asyncio

### Frontend
- **Framework**: Vue 3.5 + Vite 7
- **UI Library**: Naive UI
- **State Management**: Pinia
- **Charts**: ECharts + D3.js + @antv/g6
- **Testing**: Vitest + Playwright
- **Internationalization**: vue-i18n

### DevOps
- **Containerization**: Docker + Docker Compose
- **CI/CD**: GitHub Actions
- **Code Quality**: ESLint + Prettier + mypy

---

## 📁 Directory Structure

```
EchoLens2/
├── backend/              # Flask Python backend
│   ├── app/             # Application code
│   │   ├── api/         # API routes
│   │   ├── services/    # Business logic
│   │   └── utils/       # Utility functions
│   ├── tests/           # Test code
│   └── run.py           # Startup script
├── frontend/            # Vue 3 frontend
│   ├── src/
│   │   ├── components/  # Vue components
│   │   ├── composables/ # Composable functions
│   │   ├── views/       # Page views
│   │   ├── api/         # API client
│   │   └── i18n/        # Internationalization
│   ├── e2e/             # E2E tests
│   └── public/          # Static assets
├── docs/                # Documentation
│   ├── USER_MANUAL.md   # User manual (Chinese)
│   └── API.md           # API documentation (Chinese)
├── tools/               # Tool scripts
├── docker-compose.yml   # Docker configuration
├── DEPLOYMENT.md        # Deployment guide (Chinese)
├── PROGRESS.md          # Development progress (Chinese)
└── README.md            # This file
```

---

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

### Commit Convention

Follow Conventional Commits:

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation update
- `test:` Test related
- `refactor:` Refactoring
- `perf:` Performance optimization
- `chore:` Build/toolchain

---

## 📄 License

This project is licensed under [AGPL-3.0](LICENSE).

---

## 📧 Contact

- **Issue Tracker**: [GitHub Issues](https://github.com/zuohenlin/EchoLens2/issues)
- **Discussions**: [GitHub Discussions](https://github.com/zuohenlin/EchoLens2/discussions)
- **Email Support**: fulaoaz@qq.com

### 🔗 Links

- **Repository**: [GitHub](https://github.com/zuohenlin/EchoLens2)
- **Documentation**: [GitHub Pages](https://yourusername.github.io/echolens) *(Planned)*
- **Official Website**: *Planned*
- **Community Forum**: *Planned*

---

## 🙏 Acknowledgments

Thanks to the following open source projects:

- [OASIS](https://github.com/camel-ai/oasis) - Social media simulation framework
- [LightRAG](https://github.com/HKUDS/LightRAG) - Knowledge graph engine
- [Vue.js](https://vuejs.org/) - Progressive JavaScript framework
- [Naive UI](https://www.naiveui.com/) - Vue 3 component library
- [Flask](https://flask.palletsprojects.com/) - Python web framework

---

<div align="center">

**EchoLens 2.0** - Let Data Speak, Make Decisions Evidence-Based

Made with ❤️ by EchoLens Team

</div>
