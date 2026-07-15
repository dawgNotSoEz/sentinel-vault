# API List

Base path: `/api/v1`

## System

| Method | Endpoint | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/health` | No | Service health check |

## Authentication

| Method | Endpoint | Auth | Purpose |
| --- | --- | --- | --- |
| POST | `/auth/register` | No | Create user account |
| POST | `/auth/login` | No | Issue access and refresh tokens |
| POST | `/auth/refresh` | Refresh token | Rotate refresh token and issue new access token |
| POST | `/auth/logout` | Yes | Revoke current refresh token |
| GET | `/auth/me` | Yes | Return current user profile |

## Secrets

| Method | Endpoint | Auth | Permission | Purpose |
| --- | --- | --- | --- | --- |
| POST | `/secrets` | Yes | `secret:create` | Create encrypted secret |
| GET | `/secrets` | Yes | `secret:list` | List/search secret metadata |
| GET | `/secrets/{secret_id}` | Yes | `secret:read` | Decrypt and read secret |
| PATCH | `/secrets/{secret_id}` | Yes | `secret:update` | Update metadata |
| POST | `/secrets/{secret_id}/versions` | Yes | `secret:update` | Add new encrypted value version |
| DELETE | `/secrets/{secret_id}` | Yes | `secret:delete` | Soft delete secret |

## Categories and Tags

| Method | Endpoint | Auth | Permission | Purpose |
| --- | --- | --- | --- | --- |
| POST | `/categories` | Yes | `category:create` | Create category |
| GET | `/categories` | Yes | `category:list` | List categories |
| PATCH | `/categories/{category_id}` | Yes | `category:update` | Update category |
| DELETE | `/categories/{category_id}` | Yes | `category:delete` | Delete category if unused |

## Keys

| Method | Endpoint | Auth | Permission | Purpose |
| --- | --- | --- | --- | --- |
| GET | `/keys/keks` | Yes | `key:list` | List KEK metadata only |
| POST | `/keys/keks` | Yes | `key:create` | Generate new KEK |
| POST | `/keys/keks/rotate` | Yes | `key:rotate` | Rotate active KEK |
| GET | `/keys/deks` | Yes | `key:list` | List DEK metadata only |

## Audit

| Method | Endpoint | Auth | Permission | Purpose |
| --- | --- | --- | --- | --- |
| GET | `/audit/events` | Yes | `audit:read` | Query audit log |
| GET | `/audit/events/{event_id}` | Yes | `audit:read` | Read specific audit event |

## RBAC

| Method | Endpoint | Auth | Permission | Purpose |
| --- | --- | --- | --- | --- |
| GET | `/roles` | Yes | `role:list` | List roles |
| GET | `/permissions` | Yes | `role:list` | List permissions |
| PATCH | `/users/{user_id}/role` | Yes | `role:assign` | Assign role to user |

## Response Rules

- Never return password hashes.
- Never return raw KEK or DEK material.
- Secret value is returned only from explicit read endpoints.
- Audit events must not include secret plaintext.
