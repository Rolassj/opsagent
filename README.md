# OpsAgent

**AI-powered operational diagnostics for industrial SMBs.**

OpsAgent takes raw operational data (CSV/Excel) and delivers actionable diagnostics in plain language — no data expertise required. Upload your production, logistics, or food processing data and get KPIs, anomaly detection, and prioritized recommendations in seconds.

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-82%20passing-brightgreen.svg)](#tests)

---

## How It Works

1. **Upload** a CSV or Excel file with operational data
2. **Automatic domain detection** — manufacturing, logistics, or food processing
3. **Intelligent column mapping** — handles non-standard column names automatically
4. **Three specialized agents** process your data in sequence:
   - **Ingestion Agent** — cleans, normalizes, and validates data
   - **Analysis Agent** — calculates domain-specific KPIs and detects anomalies
   - **Recommendations Agent** — generates diagnosis and prioritized actions using Claude
5. **Download** a professional PDF report with your results

<!-- TODO: Add screenshot of the Streamlit frontend here -->
<!-- ![OpsAgent Screenshot](docs/screenshot.png) -->

---

## Features

- **Multi-domain support** — Manufacturing (OEE, defect rate), Logistics (fill rate, on-time delivery), Food processing
- **Intelligent column mapping** — Automatically maps ~50 column name variants (English/Spanish) to internal schema
- **Professional PDF reports** — Downloadable reports with executive summary, KPIs, anomalies, and recommendations
- **REST API** — FastAPI backend with 5 endpoints (diagnose, retrieve, list, PDF download, health check)
- **Authentication** — Supabase JWT auth with development mode (no auth required locally)
- **Persistent storage** — PostgreSQL via SQLAlchemy async, with in-memory fallback for development
- **82 automated tests** — Agents, API, auth, database, PDF generation, KPI calculations, column mapping

---

## Quick Start

### Prerequisites

- Python 3.11+
- [Anthropic API key](https://console.anthropic.com/)
- PostgreSQL (optional — works without it in development mode)

### Installation

```bash
# Clone the repository
git clone https://github.com/Rolassj/opsagent.git
cd opsagent

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### Running Locally

```bash
# Terminal 1: Start the API backend
uvicorn opsagent.api.main:app --reload --port 8000

# Terminal 2: Start the Streamlit frontend
streamlit run src/opsagent/app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## Architecture

```
                    ┌──────────────────────────┐
                    │     Streamlit Frontend    │
                    │   (upload, visualize,     │
                    │    download PDF)          │
                    └────────────┬─────────────┘
                                 │ HTTP (httpx)
                    ┌────────────▼─────────────┐
                    │      FastAPI Backend      │
                    │  POST /diagnose           │
                    │  GET  /diagnose/{id}      │
                    │  GET  /diagnose/{id}/pdf  │
                    │  GET  /diagnoses          │
                    │  GET  /health             │
                    └────────────┬─────────────┘
                                 │
          ┌──────────────────────▼──────────────────────┐
          │            LangGraph Pipeline               │
          │                                             │
          │  ┌───────────┐  ┌──────────┐  ┌──────────┐ │
          │  │ Ingestion │─▶│ Analysis │─▶│  Recom.  │ │
          │  │   Agent   │  │  Agent   │  │  Agent   │ │
          │  └───────────┘  └──────────┘  └──────────┘ │
          │                                             │
          └─────────────────────────────────────────────┘
                                 │
                    ┌────────────▼─────────────┐
                    │  PostgreSQL + Supabase    │
                    │  (persistence + auth)     │
                    └──────────────────────────┘
```

---

## Project Structure

```
src/opsagent/
├── agents/
│   ├── ingestion.py          # Data cleaning, column mapping, domain detection
│   ├── analysis.py           # KPI calculation, anomaly detection, trend analysis
│   └── recommendations.py    # Claude-powered diagnosis and recommendations
├── api/
│   ├── main.py               # FastAPI app with lifespan, CORS, health check
│   ├── routes.py             # REST endpoints (diagnose, retrieve, list, PDF)
│   └── schemas.py            # Pydantic models
├── auth/
│   ├── dependencies.py       # JWT validation (Supabase)
│   └── login.py              # Streamlit login/signup component
├── db/
│   ├── models.py             # SQLAlchemy model (Diagnosis table)
│   ├── session.py            # Async engine and session factory
│   └── repository.py         # CRUD operations
├── reports/
│   └── generator.py          # PDF report generation (ReportLab)
├── tools/
│   ├── data_tools.py         # Column mapping, normalization, domain detection
│   └── analysis_tools.py     # KPI formulas, anomaly detection
├── prompts/
│   └── system_prompts.py     # Claude system prompts per agent
├── config.py                 # Centralized settings from env vars
├── state.py                  # OpsAgentState (shared pipeline state)
├── graph.py                  # LangGraph build_graph() orchestrator
└── app.py                    # Streamlit frontend
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/diagnose` | Upload CSV/Excel, run pipeline, return diagnosis |
| `GET` | `/diagnose/{id}` | Retrieve a previous diagnosis by ID |
| `GET` | `/diagnose/{id}/pdf` | Download PDF report for a diagnosis |
| `GET` | `/diagnoses` | List all diagnoses for the authenticated user |
| `GET` | `/health` | Health check (API, database, auth status) |

---

## Tests

```bash
# Run all tests (82 tests)
pytest -v

# Run specific test suites
pytest tests/test_agents/ -v      # Agent tests (24)
pytest tests/test_api/ -v         # API endpoint tests (10)
pytest tests/test_auth/ -v        # Auth/JWT tests (4)
pytest tests/test_db/ -v          # Database tests (3)
pytest tests/test_reports/ -v     # PDF generation tests (8)
pytest tests/test_tools/ -v       # KPI & column mapping tests (33)
```

---

## Deployment (Railway)

### Backend (FastAPI)

1. Create a new project on [Railway](https://railway.app)
2. Connect your GitHub repo
3. Add a PostgreSQL database from Railway's plugin marketplace
4. Set environment variables:
   - `ANTHROPIC_API_KEY` — Your Claude API key
   - `ALLOWED_ORIGINS` — Frontend URL (e.g., `https://opsagent-frontend.up.railway.app`)
   - `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_JWT_SECRET` — (optional, for auth)
5. Railway detects the `Procfile` and deploys automatically

### Frontend (Streamlit)

1. Add a new service in the same Railway project
2. Set the start command: `streamlit run src/opsagent/app.py --server.port $PORT --server.address 0.0.0.0`
3. Set environment variables:
   - `OPSAGENT_API_URL` — Backend URL (e.g., `https://opsagent-api.up.railway.app`)
   - `SUPABASE_URL`, `SUPABASE_KEY` — (optional, for login)

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| AI/LLM | Claude API (claude-sonnet-4-20250514) |
| Agent Orchestration | LangGraph |
| Backend | FastAPI (async) |
| Frontend | Streamlit |
| Database | PostgreSQL + SQLAlchemy 2.0 async |
| Authentication | Supabase JWT |
| PDF Reports | ReportLab |
| Deployment | Railway |

---

## Roadmap

- [x] LangGraph mastery (Week 1)
- [x] Ingestion + Analysis Agents (Week 2)
- [x] Recommendations Agent + e2e pipeline (Week 3)
- [x] Streamlit frontend (Week 4)
- [x] FastAPI backend (Week 5)
- [x] PostgreSQL + Supabase Auth (Week 6)
- [x] PDF Report Generator (Week 7)
- [x] Hardening — column mapping, error handling, 82 tests (Week 8)
- [x] Deploy + documentation (Week 9)
- [ ] Demo, validation with real SMBs (Week 10)

---

## License

[MIT](LICENSE)

---

## Author

**Nazareno Capurro** — Industrial Engineering student building AI tools for industrial operations.

- GitHub: [@Rolassj](https://github.com/Rolassj)
