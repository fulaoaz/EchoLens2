# EchoLens 2.0 — Backend

Flask + Pydantic 2 backend for EchoLens 2.0, the e-commerce sentiment and prediction platform.
This service exposes blueprints for projects, crawler orchestration, multi-agent simulation,
time-series + causal prediction, dashboard fusion, and decision reporting.

> Clean rebuild. No code is shared with EchoLens v1; the v1 dependencies on Zep Cloud and
> camel-oasis are removed. The knowledge-graph, simulator, prediction and report layers are
> all written from scratch as a single integrated product — they do not link back to the
> legacy GraphRAG / Insight stacks at runtime.

## Requirements

- Python ≥ 3.11
- [`uv`](https://github.com/astral-sh/uv) (preferred) or `pip`

## Install

```bash
# preferred
uv sync

# fallback
python -m venv .venv
.venv\Scripts\activate         # Windows
source .venv/bin/activate      # macOS/Linux
pip install -e ".[dev]"
```

Optional heavy modeling deps (Prophet / NeuralProphet / DoWhy) live in the `prediction` extra:

```bash
uv sync --extra prediction
# or
pip install -e ".[dev,prediction]"
```

## Run

```bash
uv run python run.py
# health check
curl http://localhost:5001/health
```

## Test & Lint

```bash
uv run pytest -q
uv run ruff check .
uv run mypy app
```

## Layout

```
backend/
├── app/
│   ├── api/         # Flask blueprints
│   ├── crawler/     # crawl4ai facade + adapters + Pydantic schemas
│   ├── kg/          # Kuzu + LightRAG + NetworkX; `kg.search` is the single
│   │                #   evidence-grounded query facade for downstream layers
│   ├── simulator/   # self-research multi-agent framework
│   ├── predictor/   # Prophet/NeuralProphet + DoWhy + LLM explainer
│   ├── dashboard/   # simulation + prediction fusion
│   ├── services/    # LLM client, DuckDB store, task manager
│   ├── models/      # Pydantic domain models
│   └── utils/
├── tests/
├── pyproject.toml
├── run.py
└── Dockerfile
```
