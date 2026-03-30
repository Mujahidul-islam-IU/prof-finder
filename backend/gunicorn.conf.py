# Gunicorn configuration file for Render Free Tier
# This ensures the server doesn't time out during heavy Agent 4 processing.

import multiprocessing
import os

# ── Dynamic Port Binding ──────────────────────────────
port = os.environ.get("PORT", "8000")
bind = f"0.0.0.0:{port}"

# ── Worker Configuration ──────────────────────────────
# Use 'uvicorn.workers.UvicornWorker' if you're using FastAPI/SSE
worker_class = "uvicorn.workers.UvicornWorker"
workers = 1  # Keep it at 1 for Free Tier to avoid OOM (Out of Memory) memory issues

# ── Timeout Configuration (CRITICAL FIX) ──────────────
# Increased from 30s to 600s (10 minutes) for deep profiling
timeout = 600
graceful_timeout = 600
keepalive = 5

# ── Logging ───────────────────────────────────────────
accesslog = "-"
errorlog = "-"
loglevel = "info"
