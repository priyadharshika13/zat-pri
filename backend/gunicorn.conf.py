"""
Gunicorn configuration for production deployment.

Uses uvicorn workers for async FastAPI support.
Optimized for production workloads with proper worker management.
"""

import multiprocessing
import os

# Server socket
bind = os.getenv("GUNICORN_BIND", "0.0.0.0:8000")
backlog = int(os.getenv("GUNICORN_BACKLOG", "2048"))

# Worker processes
workers = int(os.getenv("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = int(os.getenv("GUNICORN_WORKER_CONNECTIONS", "1000"))
max_requests = int(os.getenv("GUNICORN_MAX_REQUESTS", "1000"))
max_requests_jitter = int(os.getenv("GUNICORN_MAX_REQUESTS_JITTER", "50"))
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))
keepalive = int(os.getenv("GUNICORN_KEEPALIVE", "5"))

# Logging
accesslog = os.getenv("GUNICORN_ACCESS_LOG", "-")  # stdout
errorlog = os.getenv("GUNICORN_ERROR_LOG", "-")  # stderr
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")
access_log_format = (
    '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" '
    '%(D)s %(p)s'
)

# Process naming
proc_name = "zatca-api"

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (if needed)
# keyfile = None
# certfile = None

# Preload app for better performance
preload_app = True

# Graceful timeout for worker shutdown
graceful_timeout = int(os.getenv("GUNICORN_GRACEFUL_TIMEOUT", "30"))

# Worker timeout
worker_tmp_dir = "/dev/shm"  # Use shared memory for worker temp files (faster)

# StatsD (optional, for monitoring)
# statsd_host = None
# statsd_prefix = None

