import logging
from logging.handlers import RotatingFileHandler
import sys
from pathlib import Path

def setup_logging(log_dir='logs', log_file='app.log', log_level=logging.INFO):
    # Create log directory if it doesn't exist
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)

    # Create a custom logger
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Create handlers
    c_handler = logging.StreamHandler(sys.stdout)
    f_handler = RotatingFileHandler(
        log_path / log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )

    # Create formatters and add it to handlers
    log_format = '%(asctime)s:%(levelname)s:%(name)s: %(message)s'
    c_format = logging.Formatter(log_format)
    f_format = logging.Formatter(log_format)
    c_handler.setFormatter(c_format)
    f_handler.setFormatter(f_format)

    # Add handlers to the logger
    logger.addHandler(c_handler)
    logger.addHandler(f_handler)

    return logger