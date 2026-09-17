import logging
from logging.handlers import RotatingFileHandler
import os

def setup_controller_logger(name: str = "controller") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )
        
        # Console
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        
        # Rotating File Handler
        fh = RotatingFileHandler("controller.log", maxBytes=2 * 1024 * 1024, backupCount=3)
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        
    return logger

logger = setup_controller_logger()
