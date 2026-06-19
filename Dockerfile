# syntax=docker/dockerfile:1
# Single image: builds the React SPA, then serves it from the FastAPI backend
# (same-origin -> no CORS). SQLite lives on a mounted volume at /data.

# ---- Stage 1: build the frontend ----
FROM node:22-alpine AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build   # -> /frontend/dist

# ---- Stage 2: backend + static SPA ----
FROM python:3.11-slim AS app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    STATIC_DIR=/app/static \
    SPA_API_BASE=/api \
    DATABASE_URL=sqlite:////data/tutor.db
WORKDIR /app

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
COPY --from=frontend /frontend/dist ./static

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health').status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
