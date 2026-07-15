# Architecture

```mermaid
flowchart LR
    User[User] --> UI[React Dashboard]
    UI --> API[FastAPI API]
    API --> Auth[Auth and RBAC]
    API --> Vault[Secret Engine]
    Vault --> Crypto[Envelope Encryption]
    Crypto --> KMS[Key Management]
    API --> DB[(PostgreSQL)]
    API --> Audit[Audit Log]
```
