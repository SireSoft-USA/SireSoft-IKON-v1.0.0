"""Memory-conscious production WSGI settings. Exactly one IKON model per process."""
import os
bind = os.getenv('SIREIKON_BIND', '127.0.0.1:8000')
workers = 1  # Multiple workers each allocate another LLM and GPU context.
# One thread by default: IKON GPU inference service may have mutable state.
threads = int(os.getenv('SIREIKON_THREADS', '1'))
worker_class = 'gthread'
timeout = int(os.getenv('SIREIKON_REQUEST_TIMEOUT', '600'))
graceful_timeout = 30
accesslog = '-'
errorlog = '-'
loglevel = 'info'
