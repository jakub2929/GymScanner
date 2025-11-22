import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys


def setup_logging(log_path: str, level: str):
    """Configure file + console logging with rotation."""
    log_level = getattr(logging, level.upper(), logging.INFO)

    logger = logging.getLogger()
    logger.setLevel(log_level)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handlers = []
    try:
        Path(log_path).parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_path, maxBytes=5 * 1024 * 1024, backupCount=3
        )
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
    except Exception as exc:
        # Fall back to stdout if file handler fails
        print(f"Failed to configure file logging ({exc}), using stdout only.", file=sys.stderr)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    handlers.append(console_handler)

    for handler in handlers:
        logger.addHandler(handler)

    logger.info("Logging initialized")
