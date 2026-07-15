# Sentinel Vault Backend

FastAPI backend for Sentinel Vault.

## Local Development

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e .[dev]
uvicorn app.main:app --reload
```

## Health Checks

```text
GET /api/v1/health
GET /health
```

## Tests

```bash
cd backend
pytest
```
