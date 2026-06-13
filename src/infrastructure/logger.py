import sys
import inspect
import logging
from pathlib import Path
from functools import wraps


# 設定日誌目錄（如果不存在則建立）
LOG_DIR = Path(__file__).parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

APP_LOG = LOG_DIR / "app.log"
ERROR_LOG = LOG_DIR / "error.log"

# 建立 root logger
root_logger = logging.getLogger()  # 使用全域 root logger 確保所有模組一致
root_logger.setLevel(logging.DEBUG)

# 清除所有 handler（避免重複輸出）
root_logger.handlers.clear()

# 設定顏色（Windows 相容）
if sys.platform == "win32":
    class ColorizingFormatter(logging.Formatter):
        COLORS = {
            "DEBUG": "\033[36m",      # 藍色
            "INFO": "\033[32m",       # 綠色
            "WARNING": "\033[33m",    # 黃色
            "ERROR": "\033[31m",      # 紅色
            "CRITICAL": "\033[35m",   # 紫色
        }
        RESET = "\033[0m"

        def format(self, record: logging.LogRecord):
            color = self.COLORS.get(record.levelname, "")
            levelname = record.levelname
            message = super().format(record)
            return f"{color}[{levelname}] {message}{self.RESET}"
else:
    ColorizingFormatter = logging.Formatter

# 建立格式器
common_formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# 1. Console Handler (DEBUG+)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(ColorizingFormatter(
    "%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
))

# 2. App File Handler (INFO+ 包含 WARNING, ERROR)
app_file_handler = logging.FileHandler(APP_LOG, encoding="utf-8")
app_file_handler.setLevel(logging.INFO)
app_file_handler.setFormatter(common_formatter)

# 3. Error File Handler (只限 ERROR+)
error_file_handler = logging.FileHandler(ERROR_LOG, encoding="utf-8")
error_file_handler.setLevel(logging.ERROR)
error_file_handler.setFormatter(common_formatter)

# 統一加入 root_logger
root_logger.addHandler(console_handler)
root_logger.addHandler(app_file_handler)
root_logger.addHandler(error_file_handler)

# 取得應用程式專用的 logger 實例
app_logger = logging.getLogger("cvta")

# ============================================
# 封裝化的 Logger 函式（支援 exception 捕捉）
# ============================================
def get_logger(name: str = "cvta") -> logging.Logger:
    """取得命名日誌記錄器"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    return logger


def catch_exception(func_or_logger=None):
    """
    裝飾器：捕捉 Exception 並寫入 error.log。
    支援同步 (@catch_exception) 與非同步 (@catch_exception) 函式。
    """
    def decorator(func):
        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    error_logger = get_logger(f"exception.{func.__name__}")
                    error_logger.error(
                        f"Error in {func.__name__} (Async): {str(e)}",
                        exc_info=True
                    )
                    raise
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_logger = get_logger(f"exception.{func.__name__}")
                    error_logger.error(
                        f"Error in {func.__name__} (Sync): {str(e)}",
                        exc_info=True
                    )
                    raise
            return sync_wrapper

    # 支援 @catch_exception 與 @catch_exception() 兩種寫法
    if callable(func_or_logger) and not isinstance(func_or_logger, logging.Logger):
        return decorator(func_or_logger)
    return decorator


# ============================================
# 預設 Logger 實例（全域使用）
# ============================================
def logger(
    level: str = "DEBUG",
    name: str = "cvta"
) -> logging.Logger:
    """取得命名 Logger，可指定級別"""
    return get_logger(name)


def info(message: str) -> None:
    app_logger.info(message)


def warning(message: str) -> None:
    app_logger.warning(message)


def error(message: str, exc_info: bool = False) -> None:
    app_logger.error(message, exc_info=exc_info)


def debug(message: str) -> None:
    app_logger.debug(message)


if __name__ == "__main__":
    # 測試程式碼
    debug("測試 DEBUG 級別")
    info("測試 INFO 級別")
    warning("測試 WARNING 級別 - 這只會寫入 Console 和 app.log")
    error("測試 ERROR 級別")

    # 測試 exception 捕捉
    @catch_exception()
    def test_error():
        return 1 / 0

    try:
        test_error()
    except ZeroDivisionError:
        print("Division caught")
