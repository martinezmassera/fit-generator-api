# Gunicorn configuration for Render.com
import os

# Server socket
bind = f"0.0.0.0:{os.environ.get('PORT', '5000')}"
backlog = 2048

# Worker processes
workers = 1
worker_class = "sync"
worker_connections = 1000
timeout = 120
keepalive = 2

# Restart workers after this many requests, to help prevent memory leaks
max_requests = 1000
max_requests_jitter = 100

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = "fit-generator-api"

# Server mechanics
preload_app = True
daemon = False
pidfile = None
user = None
group = None
tmp_upload_dir = None

# SSL (not needed on Render, they handle it)
keyfile = None
certfile = None