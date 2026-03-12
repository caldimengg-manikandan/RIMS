import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

def setup_logging(logs_dir: Path, debug: bool = False):
    """Sets up structured logging for the application"""
    import json
    
    class JSONFormatter(logging.Formatter):
        def format(self, record):
            log_obj = {
                "timestamp": self.formatTime(record, self.datefmt),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "module": record.module,
                "funcName": record.funcName,
            }
            if record.exc_info:
                log_obj["exception"] = self.formatException(record.exc_info)
            # Extracted extra metrics if passed via `extra={'metrics': {...}}`
            if hasattr(record, 'metrics'):
                log_obj["metrics"] = record.metrics
            return json.dumps(log_obj)
    
    # Create logs directory if it doesn't exist
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    log_level = logging.DEBUG if debug else logging.INFO
    
    # Standard format for text logs (fallback)
    log_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    json_format = JSONFormatter()
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_format)
    root_logger.addHandler(console_handler)
    
    # File handler (Rotating - JSON)
    file_handler = RotatingFileHandler(
        logs_dir / "app.log",
        maxBytes=10*1024*1024, # 10MB
        backupCount=5
    )
    file_handler.setFormatter(json_format)
    root_logger.addHandler(file_handler)
    
    # Suppress verbose logs from some libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    logging.info(f"Logging initialized in {log_level} mode. Logs saved to {logs_dir}")
