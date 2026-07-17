# Sentinel Vault

Sentinel Vault is a production-style secret management platform built like an internal security-team product, not a college CRUD app.

It stores application secrets securely using authentication, RBAC, audit trails, and envelope encryption.

## Why This Project Exists

Most portfolio projects show basic CRUD. Sentinel Vault is designed to demonstrate backend engineering, applied cryptography, secure system design, database modeling, API design, and production thinking.

## Core Capabilities Planned for v1.0

- User registration and login
- JWT access tokens and refresh-token rotation
- Argon2 password hashing
- Role-based access control
- AES-256-GCM secret encryption
- Envelope encryption with KEK and DEK hierarchy
- Secret create/read/update/delete with versions
- Categories, tags, and search
- Audit logging for security-sensitive events
- React dashboard for secrets, audit logs, keys, and settings
- Docker Compose local runtime
- Unit and integration tests
- Architecture, API, and threat-model documentation

## Tech Stack

| Area | Technology |
| --- | --- |
| Backend | Python 3.13, FastAPI |
| Database | PostgreSQL, SQLAlchemy, Alembic |
| Security | Argon2, JWT, AES-256-GCM, `cryptography` |
| Frontend | React, Tailwind CSS, Axios |
| Infrastructure | Docker, Docker Compose |
| Documentation | Markdown, Mermaid, OpenAPI |

## Architecture

```mermaid
flowchart LR
    User[User] --> UI[React Dashboard]
    UI --> API[FastAPI API]
    API --> Auth[Authentication]
    API --> RBAC[RBAC]
    API --> Vault[Secret Engine]
    Vault --> Crypto[Encryption Service]
    Crypto --> KMS[Key Management]
    API --> DB[(PostgreSQL)]
    API --> Audit[Audit Logs]
```

## Documentation

- [System Architecture](docs/architecture/system-architecture.md)
- [Folder Structure](docs/architecture/folder-structure.md)
- [Database Schema](docs/architecture/database-schema.md)
- [Backend Foundation](docs/architecture/backend-foundation.md)
- [Database Engineering](docs/architecture/database-engineering.md)
- [Authentication System](docs/architecture/authentication-system.md)
- [Cryptography](docs/architecture/cryptography.md)
- [API List](docs/api/api-list.md)
- [Threat Model](docs/threat-model/README.md)

## Getting Started

### Prerequisites
- **Python 3.13+**
- **Docker & Docker Compose** (for running the database and full stack)
- **Git**

### Running with Docker Compose (Easiest)
You can spin up the entire backend and PostgreSQL database using Docker Compose:

```bash
docker-compose up --build -d
```
The FastAPI backend will be available at `http://localhost:8000` and the interactive OpenAPI docs at `http://localhost:8000/docs`.

### Local Development Setup
To run the backend locally for development or to run tests:

1. **Navigate to the backend directory:**
   ```bash
   cd backend
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install the package and development dependencies:**
   ```bash
   pip install -e .[dev]
   ```

4. **Start the local PostgreSQL database:**
   ```bash
   # (Run this from the project root)
   docker-compose up -d db
   ```

5. **Run database migrations:**
   ```bash
   alembic upgrade head
   ```

6. **Run the local development server:**
   ```bash
   uvicorn app.main:app --reload
   ```

### Running Tests and Linters
To ensure everything is working correctly, you can run the test suite and linter:
```bash
# Run tests (runs against an in-memory SQLite database)
pytest tests/ -v

# Run linting
ruff check .
```

## Project Roadmap

| Phase | Focus | Status |
| --- | --- | --- |
| 0 | Planning, architecture, schema, API, threat model | Complete |
| 1 | Backend foundation | Complete |
| 2 | Database engineering | Complete |
| 3 | Authentication | Complete |
| 4 | Cryptography | Complete |
| 5 | Key management | Complete |
| 6 | Secret engine | Complete |
| 7 | Audit and monitoring | Complete |
| 8 | RBAC | Complete |
| 9 | Rate Limiting & Security Hardening | Complete |
| 10 | Docker and deployment | Complete |
| 11 | CI/CD & GitHub Actions | Complete |
| 12 | README Polish & Final Handover | Complete |

## Interview Story

Sentinel Vault is built to discuss secure architecture decisions:

- Why envelope encryption is used instead of directly encrypting everything with one key
- How AES-GCM provides confidentiality and integrity
- Why refresh tokens are hashed and rotated
- Why RBAC must be enforced on the backend
- How audit logging supports incident response
- How key rotation affects secret versioning

## Security Warning

This project is educational and portfolio-oriented. Do not use it to protect real production secrets until it has been independently reviewed, tested, hardened, and deployed with a real key-management strategy.
