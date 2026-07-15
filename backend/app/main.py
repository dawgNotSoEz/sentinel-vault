from fastapi import FastAPI

app = FastAPI(
    title="Sentinel Vault API",
    version="0.1.0",
    description="Internal security-team style secret management API.",
)


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "sentinel-vault-api"}
