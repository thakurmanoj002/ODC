import logging
from logging.handlers import RotatingFileHandler
import os

def setup_agent_logger(name: str = "agent") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )
        
        # Console Handler
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        
        # File Handler (rotating 2MB, keep 3 backups)
        log_file = "agent.log"
        fh = RotatingFileHandler(log_file, maxBytes=2 * 1024 * 1024, backupCount=3)
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        
    return logger

logger = setup_agent_logger()
