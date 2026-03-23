import logging
import os
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(ROOT, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# 1. Groq analysis logger (File + Console)
groq_logger = logging.getLogger("groq")
groq_logger.setLevel(logging.INFO)

# Avoid adding handlers multiple times if imported again
if not groq_logger.handlers:
    # File handler
    fh = logging.FileHandler(os.path.join(LOG_DIR, "groq.log"), encoding='utf-8')
    fh.setFormatter(logging.Formatter('%(asctime)s - %(message)s', '%H:%M:%S'))
    groq_logger.addHandler(fh)

    # Console handler
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter('%(message)s'))
    groq_logger.addHandler(ch)

def log_groq(module, category, description):
    """Log Groq analysis result to both file and console."""
    msg = f"[{module}] {category.upper()} — {description}"
    groq_logger.info(msg)

# 2. Flask server logger (File only)
def setup_server_logging(app):
    """Redirect Flask (werkzeug) logs to logs/server.log and hide from terminal."""
    log_file = os.path.join(LOG_DIR, "server.log")
    
    # Configure werkzeug logger
    w_log = logging.getLogger('werkzeug')
    
    # Remove existing handlers (usually StreamHandler)
    for handler in list(w_log.handlers):
        w_log.removeHandler(handler)
        
    # Add file handler
    fh = logging.FileHandler(log_file, encoding='utf-8')
    fh.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    w_log.addHandler(fh)
    
    # Stop propagation to root logger just in case
    w_log.propagate = False
    
    print(f"[Main] Dashboard logs redirected to {log_file}")
