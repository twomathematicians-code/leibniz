# Leibniz Proof-Engine — Docker Image
# ====================================
# Build:  docker build -t leibniz-engine -f leibniz/api/Dockerfile .
# Run:    docker run -p 8430:8430 leibniz-engine
# Context must be the repo root so the leibniz package is available.

FROM python:3.11-slim

LABEL description="Leibniz Proof-Engine API"
LABEL version="0.1.0"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY leibniz/api/requirements.txt /app/leibniz/api/requirements.txt
RUN pip install --no-cache-dir -r /app/leibniz/api/requirements.txt

# Copy only what the engine needs at runtime (no training, no .lean sources)
COPY leibniz/leibniz/ /app/leibniz/leibniz/
COPY leibniz/api/ /app/leibniz/api/
COPY leibniz/pyproject.toml /app/leibniz/pyproject.toml

# Environment
ENV PYTHONPATH=/app/leibniz
ENV PYTHONUNBUFFERED=1

# Expose the API port
EXPOSE 8430

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8430/health || exit 1

# Run the API server
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8430"]
