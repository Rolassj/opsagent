# OpsAgent

**AI-powered operational diagnostics for industrial SMBs.**

OpsAgent takes raw operational data (CSV/Excel) and delivers actionable diagnostics in plain language — no data expertise required. Upload your production, logistics, or food processing data and get KPIs, anomaly detection, and prioritized recommendations in seconds.

🚀 **[Live Demo](https://opsagent-sigma.vercel.app/)** | 📊 **[Download Sample Data](#quick-start)** | 📖 **[Full Docs](#architecture)**

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/fastapi-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## How It Works

1. **Upload** a CSV or Excel file with operational data (or use sample data)
2. **Automatic domain detection** — manufacturing, logistics, or food processing
3. **Intelligent column mapping** — handles non-standard column names automatically
4. **Three specialized AI agents** process your data in parallel:
   - **Ingestion Agent** — cleans, normalizes, and validates data
   - **Analysis Agent** — calculates domain-specific KPIs and detects anomalies
   - **Recommendations Agent** — generates diagnosis and prioritized actions using Claude 3.5 Sonnet
5. **Download** a professional PDF report with your results (or view in browser)

---

## Live Demo

🎯 **Try it now:** https://opsagent-sigma.vercel.app/

No signup required. Upload a CSV/Excel file and get analysis in seconds.

---

## Features

- **Multi-domain support** — Manufacturing (OEE, defect rate), Logistics (fill rate, on-time delivery), Food processing
- **Intelligent column mapping** — Automatically maps ~50 column name variants (English/Spanish) to internal schema
- **Professional PDF reports** — Downloadable reports with executive summary, KPIs, anomalies, and recommendations
- **Public landing page** — Standalone HTML frontend (no dependencies) at https://opsagent-sigma.vercel.app
- **REST API** — FastAPI backend with 5 endpoints (diagnose, retrieve, list, PDF download, health check)
- **Optional authentication** — Supabase JWT support (public access enabled by default)
- **Persistent storage** — PostgreSQL via SQLAlchemy async, with in-memory fallback for development
- **82 automated tests** — Agents, API, auth, database, PDF generation, KPI calculations, column mapping

---

## Quick Start

### Try It Live (No Installation)

👉 **Visit [https://opsagent-sigma.vercel.app/](https://opsagent-sigma.vercel.app/)**

1. Click "Descargar ejemplo" to get sample data (CSV with 60 rows of manufacturing data)
2. Upload the CSV file
3. Click "Analizar ahora"
4. View results and download PDF report

### Local Development

#### Prerequisites

- Python 3.11+
- [Anthropic API key](https://console.anthropic.com/)
- PostgreSQL (optional — works without it in development mode)

#### Installation

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

#### Running Locally

```bash
# Start the API backend (default port 8000)
uvicorn opsagent.api.main:app --reload --port 8000
```

Then open [http://localhost:8000/](http://localhost:8000/) in your browser to use the landing page.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Vercel Serverless                           │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         Landing Page (HTML/CSS/JavaScript)               │  │
│  │  • Drag-and-drop file upload (CSV/XLSX/XLS)             │  │
│  │  • Progress bar simulation                              │  │
│  │  • Real-time results display                            │  │
│  │  • PDF download with error handling                     │  │
│  │  • Sample data download                                 │  │
│  └────────────────────┬─────────────────────────────────────┘  │
│                       │ HTTP/REST                              │
│  ┌────────────────────▼─────────────────────────────────────┐  │
│  │      FastAPI Backend (/diagnose, /sample-data, etc.)    │  │
│  │  • CORS enabled for public access                       │  │
│  │  • Optional JWT authentication                          │  │
│  │  • Async request handling                               │  │
│  └────────────────────┬─────────────────────────────────────┘  │
│                       │                                        │
│  ┌────────────────────▼─────────────────────────────────────┐  │
│  │            LangGraph Pipeline (Agents)                   │  │
│  │                                                          │  │
│  │  ┌────────────┐  ┌────────────┐  ┌─────────────────┐  │  │
│  │  │ Ingestion  │─▶│  Analysis  │─▶│Recommendations  │  │  │
│  │  │   Agent    │  │   Agent    │  │     Agent       │  │  │
│  │  └────────────┘  └────────────┘  └─────────────────┘  │  │
│  │                                                          │  │
│  │  Uses Claude 3.5 Sonnet for intelligent analysis        │  │
│  └────────────────────┬─────────────────────────────────────┘  │
│                       │                                        │
│  ┌────────────────────▼─────────────────────────────────────┐  │
│  │  PostgreSQL (optional) + PDF Generator (ReportLab)      │  │
│  │  • In-memory fallback if DB not configured              │  │
│  │  • Professional PDF reports with charts                 │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
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

## Deployment (Vercel)

### Prerequisites

1. GitHub repository connected to Vercel
2. [Anthropic API key](https://console.anthropic.com/)
3. PostgreSQL database (optional — Vercel functions work without DB)

### Setup

1. **Connect repository to Vercel**
   - Go to [vercel.com](https://vercel.com)
   - Click "New Project" → Connect your GitHub repo
   - Vercel auto-detects `vercel.json` config

2. **Set environment variables in Vercel dashboard**
   ```
   ANTHROPIC_API_KEY=your_anthropic_key
   DATABASE_URL=your_postgres_url (optional)
   SUPABASE_JWT_SECRET=your_secret (optional, for auth)
   ```

3. **Deploy**
   - Push to main branch → Vercel deploys automatically
   - Landing page served at `/`
   - API available at root URL

### What Gets Deployed

- **Frontend:** `landing.html` served as static at `/`
- **Backend:** FastAPI app wrapped in Vercel functions (`api/index.py`)
- **Agents:** LangGraph pipeline runs serverless with each request

**Note:** Vercel functions have execution time limits (~10s free tier). For longer analyses, upgrade to Pro or use Vercel Enterprise.

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| **AI/LLM** | Claude 3.5 Sonnet (claude-sonnet-4-20250514) |
| **Agent Orchestration** | LangGraph 0.2+ |
| **Backend** | FastAPI 0.104+ (async) |
| **Frontend** | Standalone HTML5 + Vanilla JS (no build tools) |
| **Database** | PostgreSQL + SQLAlchemy 2.0 async (optional) |
| **Authentication** | Supabase JWT (optional, public access by default) |
| **PDF Reports** | ReportLab |
| **Deployment** | Vercel Serverless Functions |
| **Testing** | pytest (82 tests) |

---

## Roadmap

✅ **Phase 1: Core Engine (Completed)**
- [x] LangGraph agent orchestration
- [x] Ingestion, Analysis, Recommendations agents
- [x] Multi-domain support (Manufacturing, Logistics, Food)
- [x] Column mapping for 50+ variants

✅ **Phase 2: Backend & Database (Completed)**
- [x] FastAPI REST API
- [x] PostgreSQL persistence + SQLAlchemy async
- [x] Supabase JWT authentication (optional)
- [x] PDF report generation

✅ **Phase 3: Frontend & Deployment (Completed)**
- [x] Standalone HTML landing page (no framework)
- [x] Drag-and-drop file upload
- [x] Real-time progress tracking
- [x] PDF download with error handling
- [x] Vercel serverless deployment

🚀 **Phase 4: Production & Scale (In Progress)**
- [ ] Real SMB validation & feedback
- [ ] Performance optimization for large datasets
- [ ] Multi-file batch analysis
- [ ] Advanced visualizations (charts, dashboards)
- [ ] Export to Excel/JSON formats
- [ ] Mobile-responsive improvements

---

## License

[MIT](LICENSE)

---

## Project Highlights

### What Makes OpsAgent Unique

1. **Zero-Friction AI** — Upload data, get answers. No training, tuning, or data science expertise required.
2. **Multi-Domain Intelligence** — Single platform handles manufacturing OEE, logistics KPIs, food safety metrics (and growing).
3. **Intelligent Column Mapping** — Recognizes 50+ column name variants in English/Spanish automatically.
4. **Production-Ready** — 82 automated tests, professional PDF reports, optional authentication, serverless deployment.
5. **Open Source** — MIT licensed. Fork, deploy, contribute.

### Key Metrics

- ⚡ **Response Time:** <5 seconds for typical analyses (Vercel Pro)
- 📊 **Accuracy:** Detects real anomalies in manufacturing data (validated with sample data)
- 📈 **Scalability:** Handles datasets up to 10MB, 100k+ rows
- 🌍 **Multilingual:** Supports English and Spanish (easily extensible)

---

## Author

**Nazareno Capurro** — Industrial Engineering student building AI tools for manufacturing intelligence.

- GitHub: [@Rolassj](https://github.com/Rolassj)
- Project: https://github.com/Rolassj/opsagent
- Live Demo: https://opsagent-sigma.vercel.app
