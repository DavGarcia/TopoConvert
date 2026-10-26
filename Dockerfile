# ==============================================================================
# Stage 1: Build the RTL Persian React + TypeScript + Vite Frontend
# ==============================================================================
FROM node:22-slim AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm install --no-audit --no-fund

COPY frontend/ ./
RUN mkdir -p /app/survey_web/static_bundle && npm run build

# ==============================================================================
# Stage 2: Production Python 3.11 FastAPI + Survey Core Runtime
# ==============================================================================
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /app

# Install system dependencies required by pyproj/scipy/matplotlib
RUN apt-get update && apt-get install -y --no-install-recommends \
    libexpat1 \
    && rm -rf /var/lib/apt/lists/*

# Copy package manifests & source modules
COPY pyproject.toml README.md LICENSE ./
COPY topoconvert/ ./topoconvert/
COPY survey_core/ ./survey_core/
COPY survey_web/ ./survey_web/
COPY samples/ ./samples/

# Copy compiled static frontend bundle (including self-hosted Vazirmatn fonts)
COPY --from=frontend-builder /app/survey_web/static_bundle/ ./survey_web/static_bundle/

# Install TopoConvert + Web API dependencies
RUN pip install --upgrade pip && \
    pip install .

# Run as non-root user for security
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request, os; port = os.environ.get('PORT', '8000'); urllib.request.urlopen(f'http://127.0.0.1:{port}/healthz', timeout=3)" || exit 1

CMD ["sh", "-c", "uvicorn survey_web.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
