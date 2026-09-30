# Leibniz — Streamlit app container (Azure-ready)
# Build:   docker build -t leibniz-app -f deploy/Dockerfile.streamlit .
# Run:     docker run -p 8501:8501 leibniz-app

FROM python:3.11-slim

LABEL description="SCITAMEHTAM Leibniz — the mathematician's engine (Streamlit app)"
LABEL version="1.0.0"

WORKDIR /app

# System deps (curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Python deps first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY leibniz/ ./leibniz/
COPY app/ ./app/
COPY streamlit_app.py .

# Streamlit must listen on 0.0.0.0 and the port Azure injects (default 8501)
ENV PYTHONUNBUFFERED=1
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=40s \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "streamlit_app.py", \
     "--server.port=8501", "--server.address=0.0.0.0", \
     "--server.headless=true"]
