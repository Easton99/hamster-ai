import logging
import logging.handlers
from pathlib import Path

_SENSITIVE_TERMS = ("password", "token", "secret", "private_mode_data", "work_data")


class _SensitiveFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = str(record.getMessage()).lower()
        for term in _SENSITIVE_TERMS:
            if term in msg:
                record.msg = "[REDACTED — sensitive term detected]"
                record.args = ()
                break
        return True


def setup_logging(log_level: str = "INFO", log_dir: Path = Path("data/logs")) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("hamster_ai")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    if logger.handlers:
        return logger  # already configured (e.g. called twice)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    sensitive_filter = _SensitiveFilter()

    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "hamster_ai.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(sensitive_filter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.addFilter(sensitive_filter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
