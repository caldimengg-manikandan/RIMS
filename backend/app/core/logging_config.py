import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

def setup_logging(logs_dir: Path = None, debug: bool = False):
    """Sets up structured logging for the application"""
    
    log_level = logging.DEBUG if debug else logging.INFO
    
    # Standard format for text logs
    log_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_format)
    root_logger.addHandler(console_handler)
    
    # File handler (Rotating) only if logs_dir is provided
    if logs_dir:
        try:
            logs_dir.mkdir(parents=True, exist_ok=True)
            file_handler = RotatingFileHandler(
                logs_dir / "app.log",
                maxBytes=10*1024*1024, # 10MB
                backupCount=5,
                encoding="utf-8"
            )
            file_handler.setFormatter(log_format)
            root_logger.addHandler(file_handler)
            logging.info(f"Logging initialized. File logs saved to {logs_dir}")
        except Exception as e:
            logging.warning(f"Failed to initialize file logging: {e}. Falling back to console only.")
    else:
        logging.info(f"Logging initialized in console-only mode.")
    
    # Suppress verbose logs from some libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
