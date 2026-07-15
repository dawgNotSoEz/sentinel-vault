# Folder Structure

```text
sentinel-vault/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/              # Versioned API routers
│   │   ├── core/                # Config, logging, app settings
│   │   ├── db/                  # SQLAlchemy session, base model, migrations glue
│   │   ├── models/              # SQLAlchemy ORM models
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   ├── security/            # JWT, Argon2, crypto helpers, authorization
│   │   ├── services/            # Business logic layer
│   │   └── main.py              # FastAPI app entrypoint
│   ├── tests/                   # Backend unit/integration tests
│   └── pyproject.toml           # Backend dependencies and tooling
├── frontend/
│   ├── src/
│   │   ├── components/          # Reusable UI components
│   │   ├── hooks/               # React hooks
│   │   ├── lib/                 # Axios client, utilities
│   │   └── pages/               # Dashboard, login, secrets, audit, keys
│   └── package.json
├── docs/
│   ├── api/                     # API list and OpenAPI notes
│   ├── architecture/            # System design, diagrams, folder structure
│   └── threat-model/            # Security assumptions, threats, mitigations
├── infra/
│   ├── docker/                  # Dockerfiles and runtime config
│   └── scripts/                 # Local/dev automation scripts
├── .github/workflows/           # CI pipeline later
├── .env.example                 # Safe development config example
├── .gitignore
├── docker-compose.yml
└── README.md
```

## Design Rule

The API layer should stay thin. Real business logic belongs in services, database shape belongs in models, validation belongs in schemas, and security-sensitive helpers belong in `security/`.
