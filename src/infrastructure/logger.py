import logging
import os
from pathlib import Path
from typing import Optional
from functools import wraps


# 設定日誌目錄（如果不存在則建立）
LOG_DIR = Path(__file__).parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

APP_LOG = LOG_DIR / "app.log"
ERROR_LOG = LOG_DIR / "error.log"

# 建立 root logger
root_logger = logging.getLogger("cvta")
root_logger.setLevel(logging.DEBUG)

# 清除所有 handler（避免重複輸出）
root_logger.handlers.clear()

# 建立 Console Handler（彩色輸出）
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# 設定顏色（Windows 相容）
import sys
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

        def format(self, record):
            color = self.COLORS.get(record.levelname, "")
            levelname = record.levelname
            message = super().format(record)
            return f"{color}[{levelname}] {message}{self.RESET}"

    console_handler.setFormatter(ColorizingFormatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))

# 建立 File Handler（雙寫 app.log）
file_handler = logging.FileHandler(APP_LOG, encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
))

# Debug/Info 只寫 Console，Warning/Error/ Critical 雙寫
console_handler.setLevel(logging.DEBUG)
file_handler.setLevel(logging.WARNING)

root_logger.addHandler(console_handler)
root_logger.addHandler(file_handler)


# ============================================
# 封裝化的 Logger 函式（支援 exception 捕捉）
# ============================================
def get_logger(name: str = "cvta") -> logging.Logger:
    """取得命名日誌記錄器"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    if logger.handlers:  # 避免重複處理
        return logger
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    return logger


def catch_exception(logger: logging.Logger = None):
    """裝飾器：捕捉 Exception 並寫入 error.log"""
    if logger is None:
        logger = get_logger("cvta")
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # 寫入 error.log（包含 Traceback）
                error_logger = get_logger("error")
                error_logger.error(
                    f"Error in {func.__name__}: {str(e)}",
                    exc_info=True
                )
                raise
        return wrapper
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
    print(f"[INFO] {message}")
    logging.info(message)


def warning(message: str) -> None:
    print(f"[WARNING] {message}")
    logging.warning(message)


def error(message: str, exc_info: bool = False) -> None:
    print(f"[ERROR] {message}")
    logging.error(message, exc_info=exc_info)


def debug(message: str) -> None:
    print(f"[DEBUG] {message}")
    logging.debug(message)


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