# Gunicorn configuration file
import multiprocessing

# Bind to port 8000 on all available network interfaces
bind = "127.0.0.1:8000"

# Number of worker processes
workers = 3

# Worker class to use
worker_class = "sync"

# Timeout for worker processes (in seconds)
timeout = 120

# Log level
loglevel = "info"

# Access log format
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr

# Preload application code before forking worker processes
preload_app = True

# Reload workers when code changes (for development)
# Set to False in production
reload = False