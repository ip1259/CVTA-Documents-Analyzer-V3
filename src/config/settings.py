# -*- coding: utf-8 -*-
"""CVTA 全域設定檔 - 系統參數與環境變數配置"""

import os
import configparser
from pathlib import Path
from typing import Union, Optional

# 定義目錄結構
CONFIG_DIR = Path(__file__).parent.resolve()
BASE_DIR = CONFIG_DIR.parent

# --- 1. 定義系統預設值 (程式碼內的基準設定) ---
# Ollama 多模態模型設定
OLLAMA_HOST = "http://HOST:PORT"
OLLAMA_MODEL = "qwen3.5:9b"
# 系統參數
SYSTEM_NAME = "公文 OCR 自動化歸納系統"
VERSION = "3.0.0"
SYSTEM_LANGUAGE = "zh-TW"
# 業務規則
DATE_VALIDATION_DAYS = 90
# 日誌設定
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DIR = "logs"
# 資料儲存設定
DATA_DIR = "data"
INPUT_DIR = "input_scans"
OUTPUT_DIR = "output_results"

# Google API 認證金鑰路徑 (動態計算，不建議寫入 config)
GOOGLE_KEY_PATH = CONFIG_DIR / "google_key.json"
GOOGLE_CLIENT_SECRET_PATH = CONFIG_DIR / "client_secret.json"
GOOGLE_TOKEN_PATH = CONFIG_DIR / "token.json"


# 運作參數
GOOGLE_SPREADSHEET_ID: Optional[str] = None
SHEET_NAME: Optional[str] = None
TARGET_FOLDER_NAME: Optional[str] = None
PROMPTS_PATH: Union[str, Path] = CONFIG_DIR / "prompts.json"


# --- 2. 自動建立預設 config 檔 (若不存在任何 .cfg) ---
def _ensure_default_config():
    """檢查 settings.cfg 是否存在，並自動補齊缺失的 Section 或 Key，而不覆蓋既有設定。"""
    default_cfg_path = CONFIG_DIR / "settings.cfg"
    config = configparser.ConfigParser(interpolation=None)

    # 如果檔案已存在，先載入既有設定
    if default_cfg_path.exists():
        config.read(default_cfg_path, encoding='utf-8')

    # 定義預期要有的完整結構與預設值
    required_structure = {
        'Ollama': {
            'OLLAMA_HOST': OLLAMA_HOST,
            'OLLAMA_MODEL': OLLAMA_MODEL,
            'PROMPTS_PATH': str(PROMPTS_PATH)
        },
        'System': {
            'SYSTEM_NAME': SYSTEM_NAME,
            'VERSION': VERSION,
            'SYSTEM_LANGUAGE': SYSTEM_LANGUAGE
        },
        'Rules': {'DATE_VALIDATION_DAYS': str(DATE_VALIDATION_DAYS)},
        'Logging': {
            'LOG_LEVEL': LOG_LEVEL,
            'LOG_FORMAT': LOG_FORMAT,
            'LOG_DIR': LOG_DIR
        },
        'Storage': {
            'DATA_DIR': DATA_DIR,
            'INPUT_DIR': INPUT_DIR,
            'OUTPUT_DIR': OUTPUT_DIR
        },
        'Google': {
            'GOOGLE_SPREADSHEET_ID': '',
            'SHEET_NAME': '',
            'TARGET_FOLDER_NAME': ''
        }
    }

    modified = False
    for section, options in required_structure.items():
        if not config.has_section(section):
            config.add_section(section)
            modified = True

        for key, value in options.items():
            if not config.has_option(section, key):
                config.set(section, key, str(value))
                modified = True

    # 只有在有新增內容或檔案不存在時才寫入磁碟
    if modified or not default_cfg_path.exists():
        with open(default_cfg_path, 'w', encoding='utf-8') as f:
            config.write(f)


_ensure_default_config()


# --- 3. 載入所有 .cfg 設定檔並蓋掉預設值 ---
for cfg_file in sorted(os.listdir(CONFIG_DIR), key=str.lower):
    if cfg_file.endswith('.cfg'):
        cfg_path = CONFIG_DIR / cfg_file
        parser = configparser.ConfigParser(interpolation=None)
        parser.read(cfg_path, encoding='utf-8')
        for section in parser.sections():
            for key, value in parser[section].items():
                # 將 Key 轉為大寫以對應 Python 常數變數名
                key_upper = key.upper()

                # 自動轉型邏輯
                final_val = value
                try:
                    if value.lower() == 'true':
                        final_val = True
                    elif value.lower() == 'false':
                        final_val = False
                    elif '.' in value:
                        final_val = float(value)
                    else:
                        final_val = int(value)
                except (ValueError, TypeError):
                    final_val = value

                # 更新全域變數，這會蓋掉第一階段定義的預設值
                globals()[key_upper] = final_val
