# https://docs.gunicorn.org/en/stable/settings.html
bind = "0.0.0.0:8080"
# Enable prints to be shown immediately
accesslog = "-"  # Print access log to stdout
errorlog = "-"   # Print error log to stdout
capture_output = True
enable_stdio_inheritance = True

# Optimized for I/O-bound workloads (API calls to Google Sheets)
# 4 workers × 4 threads = 16 concurrent requests (3-4x throughput improvement)
workers = 4
threads = 4
timeout = 360

# Connection pooling works best with worker_class = "sync" (default)
# Each worker reuses HTTP connections via requests.Session
