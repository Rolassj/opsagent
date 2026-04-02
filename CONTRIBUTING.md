# Contributing to OpsAgent

Thanks for your interest in contributing to OpsAgent!

## Development Setup

1. Clone the repository
2. Create a virtual environment: `python -m venv .venv`
3. Activate it: `source .venv/bin/activate` (or `.venv\Scripts\activate` on Windows)
4. Install dependencies: `pip install -e ".[dev]"`
5. Copy `.env.example` to `.env` and add your API keys
6. Run tests: `pytest`

## Running Locally

```bash
# Start the API backend
uvicorn opsagent.api.main:app --reload --port 8000

# In another terminal, start the frontend
streamlit run src/opsagent/app.py
```

## Running Tests

```bash
# All tests (excluding integration)
pytest

# With verbose output
pytest -v

# Including integration tests (requires ANTHROPIC_API_KEY)
pytest -m integration
```

## Code Style

- Python 3.11+
- Type hints where practical
- Docstrings on public functions
- Tests for new functionality

## Pull Requests

1. Create a feature branch from `main`
2. Make your changes
3. Run `pytest` and ensure all tests pass
4. Submit a PR with a clear description
