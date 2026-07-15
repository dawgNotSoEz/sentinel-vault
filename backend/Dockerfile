FROM python:3.13-slim

WORKDIR /app

# Install system dependencies if required (e.g., libpq-dev for psycopg if not using binary)
# psycopg[binary] is used so we don't strictly need libpq-dev, but it's good practice
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml /app/
RUN pip install --no-cache-dir .

COPY . /app/

# Create a non-root user for security
RUN useradd -m appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
