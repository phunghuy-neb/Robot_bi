"""
log_config.py — Logging configuration cho Robot Bi.
Gọi setup_logging() một lần duy nhất khi startup.
"""
import logging
import logging.handlers
import os
from pathlib import Path


def setup_logging() -> None:
    """
    Cấu hình logging cho toàn bộ ứng dụng:
      - File handler: DEBUG+ → logs/robot_bi.log (RotatingFileHandler 5MB x3)
      - Console handler: WARNING+ (không spam INFO khi chạy thật)
    """
    log_dir = Path(__file__).parent.parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "robot_bi.log"
    log_level_str = os.getenv("LOG_LEVEL", "DEBUG").upper()
    log_level = getattr(logging, log_level_str, logging.DEBUG)

    robot_logger = logging.getLogger("robot_bi")
    has_file_handler = any(
        isinstance(h, logging.handlers.RotatingFileHandler)
        for h in robot_logger.handlers
    )
    if has_file_handler:
        return

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(max(log_level, logging.WARNING))
    console_handler.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(log_level)
    root.addHandler(file_handler)
    root.addHandler(console_handler)

    robot_logger.setLevel(log_level)
    robot_logger.addHandler(file_handler)
    robot_logger.addHandler(console_handler)
    robot_logger.propagate = False

    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
