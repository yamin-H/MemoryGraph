FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy packaging and dependencies first for layer caching
COPY requirements.txt pyproject.toml README.md ./
COPY src /app/src

RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir -e .

# Copy application code
COPY apps/api /app/apps/api
COPY data /app/data
COPY scripts /app/scripts

WORKDIR /app/apps/api

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
