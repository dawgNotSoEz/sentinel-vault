# Database Schema

## Entity Relationship Diagram

```mermaid
erDiagram
    USERS ||--o{ REFRESH_TOKENS : owns
    USERS ||--o{ SECRETS : creates
    USERS ||--o{ AUDIT_LOGS : triggers
    USERS }o--|| ROLES : has
    ROLES ||--o{ ROLE_PERMISSIONS : grants
    PERMISSIONS ||--o{ ROLE_PERMISSIONS : included_in
    CATEGORIES ||--o{ SECRETS : groups
    SECRETS ||--o{ SECRET_VERSIONS : versions
    KEKS ||--o{ DEKS : wraps
    DEKS ||--o{ SECRET_VERSIONS : encrypts

    USERS {
        uuid id PK
        string email UK
        string password_hash
        string full_name
        uuid role_id FK
        boolean is_active
        datetime created_at
        datetime updated_at
    }

    ROLES {
        uuid id PK
        string name UK
        string description
    }

    PERMISSIONS {
        uuid id PK
        string name UK
        string description
    }

    ROLE_PERMISSIONS {
        uuid role_id FK
        uuid permission_id FK
    }

    REFRESH_TOKENS {
        uuid id PK
        uuid user_id FK
        string token_hash
        datetime expires_at
        datetime revoked_at
        datetime created_at
    }

    CATEGORIES {
        uuid id PK
        string name
        string description
        uuid created_by FK
        datetime created_at
    }

    SECRETS {
        uuid id PK
        string name
        string description
        uuid category_id FK
        uuid created_by FK
        datetime created_at
        datetime updated_at
        datetime deleted_at
    }

    SECRET_VERSIONS {
        uuid id PK
        uuid secret_id FK
        integer version
        bytes ciphertext
        bytes nonce
        bytes auth_tag
        uuid dek_id FK
        string metadata_json
        datetime created_at
    }

    KEKS {
        uuid id PK
        integer version
        string status
        bytes encrypted_key_material
        datetime created_at
        datetime rotated_at
    }

    DEKS {
        uuid id PK
        uuid kek_id FK
        bytes encrypted_key_material
        integer kek_version
        datetime created_at
    }

    AUDIT_LOGS {
        uuid id PK
        uuid user_id FK
        string action
        string resource_type
        uuid resource_id
        string ip_address
        string user_agent
        string outcome
        string metadata_json
        datetime created_at
    }
```

## Indexing Plan

| Table | Index | Why |
| --- | --- | --- |
| users | email unique | Login lookup |
| refresh_tokens | token_hash unique | Refresh validation |
| secrets | name, category_id | Search and filtering |
| secret_versions | secret_id, version unique | Fast latest-version lookup |
| audit_logs | user_id, created_at | User activity timeline |
| audit_logs | action, created_at | Security investigations |
| keks | version unique | Key rotation lookup |

## Normalization Notes

- Secret metadata and encrypted values are separated through `secret_versions`.
- Role permissions use a join table to avoid hardcoding authorization in user rows.
- Refresh tokens are stored hashed, not plaintext.
- Soft delete is used for secrets so audit history remains explainable.
