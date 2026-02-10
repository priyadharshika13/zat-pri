# Multi-stage Dockerfile for production deployment
# Stage 1: Build dependencies
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
COPY gunicorn.conf.py .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Production image
FROM python:3.11-slim

WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/logs /app/certs && \
    chown -R appuser:appuser /app

# Copy application code
COPY --chown=appuser:appuser app ./app
COPY --chown=appuser:appuser alembic.ini .
COPY --chown=appuser:appuser alembic ./alembic

# Set working directory permissions
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/api/v1/health', timeout=5.0)" || exit 1

# Use gunicorn with uvicorn workers for production
CMD ["gunicorn", "app.main:app", "-c", "gunicorn.conf.py"]
