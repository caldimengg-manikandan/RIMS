import multiprocessing
import os

# Gunicorn configuration for production FastAPI deployment
# No source code modification required.

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
# Ideal number of workers is (2 * cores) + 1
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
timeout = 30
keepalive = 5

# Logging
accesslog = "logs/gunicorn_access.log"
errorlog = "logs/gunicorn_error.log"
loglevel = "info"

# Process naming
proc_name = "ars_backend_prod"

# Performance tuning
max_requests = 1000
max_requests_jitter = 50
