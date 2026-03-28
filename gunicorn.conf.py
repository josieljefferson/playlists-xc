import os

bind = f"0.0.0.0:{os.getenv('PORT', 5000)}"
workers = int(os.getenv("GUNICORN_WORKERS", "4"))
worker_class = "sync"
worker_connections = 1000
timeout = 120
keepalive = 5
max_requests = 1000
max_requests_jitter = 50
loglevel = "info"
accesslog = "-"
errorlog = "-"