import os
import multiprocessing

# Gunicorn configuration
bind = "0.0.0.0:" + os.getenv("PORT", "10000")
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
loglevel = "info"
accesslog = "-"
errorlog = "-"
timeout = 120
keepalive = 5
