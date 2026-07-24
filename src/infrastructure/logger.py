import inspect
import logging
import sys
from functools import wraps
from pathlib import Path


LOGGER_NAME = "cvta"
app_logger = logging.getLogger(LOGGER_NAME)
app_logger.addHandler(logging.NullHandler())
app_logger.propagate = False


class ColorizingFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": "\033[36m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[35m",
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        color = self.COLORS.get(record.levelname, "")
        return f"{color}{message}{self.RESET}"


def initialize_logging(log_dir: str | Path | None = None) -> logging.Logger:
    """Initialize project logging once from an application entry point."""
    if getattr(app_logger, "_cvta_initialized", False):
        return app_logger

    target_dir = (
        Path(log_dir)
        if log_dir is not None
        else Path(__file__).resolve().parents[2] / "logs"
    )
    target_dir.mkdir(parents=True, exist_ok=True)

    app_logger.handlers.clear()
    app_logger.setLevel(logging.DEBUG)

    common_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_formatter: logging.Formatter
    if sys.platform == "win32":
        console_formatter = ColorizingFormatter(
            "%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    else:
        console_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(console_formatter)

    app_handler = logging.FileHandler(
        target_dir / "app.log",
        encoding="utf-8",
    )
    app_handler.setLevel(logging.INFO)
    app_handler.setFormatter(common_formatter)

    error_handler = logging.FileHandler(
        target_dir / "error.log",
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(common_formatter)

    app_logger.addHandler(console_handler)
    app_logger.addHandler(app_handler)
    app_logger.addHandler(error_handler)
    app_logger._cvta_initialized = True
    return app_logger


def get_logger(name: str = LOGGER_NAME) -> logging.Logger:
    if name == LOGGER_NAME:
        return app_logger
    return app_logger.getChild(name.removeprefix(f"{LOGGER_NAME}."))


def catch_exception(func_or_logger=None):
    def decorator(func):
        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except Exception:
                    get_logger(f"exception.{func.__name__}").exception(
                        f"Error in {func.__name__} (Async)"
                    )
                    raise
            return async_wrapper

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception:
                get_logger(f"exception.{func.__name__}").exception(
                    f"Error in {func.__name__} (Sync)"
                )
                raise
        return sync_wrapper

    if callable(func_or_logger) and not isinstance(
        func_or_logger,
        logging.Logger,
    ):
        return decorator(func_or_logger)
    return decorator


def logger(level: str = "DEBUG", name: str = LOGGER_NAME) -> logging.Logger:
    return get_logger(name)


def info(message: str) -> None:
    app_logger.info(message)


def warning(message: str) -> None:
    app_logger.warning(message)


def error(message: str, exc_info: bool = False) -> None:
    app_logger.error(message, exc_info=exc_info)


def debug(message: str) -> None:
    app_logger.debug(message)
