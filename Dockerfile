# Multi-stage Dockerfile for Ephemeral Notes
# Build stage: install dependencies
FROM python:3.12-slim AS build
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./
RUN python -m pip install --upgrade pip setuptools wheel
RUN python -m pip install --prefix=/install -r requirements.txt
# Final stage: copy only runtime artifacts
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
# Create a non-root user
RUN groupadd -r app && useradd --no-log-init -r -g app app
# Copy installed packages from build stage
COPY --from=build /install /usr/local
# Copy application code
COPY . /app
RUN chown -R app:app /app
USER app
EXPOSE 8080
ENV PORT=8080
CMD ["gunicorn", "-w", "2", "-k", "gthread", "-b", "0.0.0.0:8080", "app:app"]
# Docker support intentionally removed
# This project is currently configured to run locally only (python3 app.py or gunicorn).
# If you want Docker support again in the future, ask and it can be re-added.
