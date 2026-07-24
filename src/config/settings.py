# -*- coding: utf-8 -*-
"""CVTA 全域設定檔 - 系統參數與環境變數配置"""

import os
import configparser
from pathlib import Path
from typing import Union, Optional

CONFIG_DIR = Path(__file__).parent.resolve()
BASE_DIR = CONFIG_DIR.parent

DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11434"
OLLAMA_HOST = DEFAULT_OLLAMA_HOST
OLLAMA_MODEL = "qwen3.5:9b"
OLLAMA_HEALTH_TIMEOUT = 5
OLLAMA_REQUEST_TIMEOUT = 300
SYSTEM_NAME = "公文 OCR 自動化歸納系統"
VERSION = "3.0.0"
SYSTEM_LANGUAGE = "zh-TW"
DATE_VALIDATION_DAYS = 90
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DIR = "logs"
DATA_DIR = "data"
INPUT_DIR = "input_scans"
OUTPUT_DIR = "output_results"

GOOGLE_KEY_PATH = CONFIG_DIR / "google_key.json"
GOOGLE_CLIENT_SECRET_PATH = CONFIG_DIR / "client_secret.json"
GOOGLE_TOKEN_PATH = CONFIG_DIR / "token.json"


GOOGLE_SPREADSHEET_ID: Optional[str] = None
SHEET_NAME: Optional[str] = None
TARGET_FOLDER_NAME: Optional[str] = None
PROMPTS_PATH: Union[str, Path] = CONFIG_DIR / "prompts.json"


def _ensure_default_config():
    """檢查 settings.cfg 是否存在，並自動補齊缺失的 Section 或 Key，而不覆蓋既有設定。"""
    default_cfg_path = CONFIG_DIR / "settings.cfg"
    config = configparser.ConfigParser(interpolation=None)

    if default_cfg_path.exists():
        config.read(default_cfg_path, encoding='utf-8')

    required_structure = {
        'Ollama': {
            'OLLAMA_HOST': DEFAULT_OLLAMA_HOST,
            'OLLAMA_MODEL': OLLAMA_MODEL,
            'OLLAMA_HEALTH_TIMEOUT': str(OLLAMA_HEALTH_TIMEOUT),
            'OLLAMA_REQUEST_TIMEOUT': str(OLLAMA_REQUEST_TIMEOUT),
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

    config_created = not default_cfg_path.exists()
    if modified or config_created:
        with open(default_cfg_path, 'w', encoding='utf-8') as f:
            config.write(f)

    return config_created


# GUI 以此旗標判斷本次啟動是否需要引導使用者完成設定。
CONFIG_WAS_CREATED = _ensure_default_config()


for cfg_file in sorted(os.listdir(CONFIG_DIR), key=str.lower):
    if cfg_file.endswith('.cfg'):
        cfg_path = CONFIG_DIR / cfg_file
        parser = configparser.ConfigParser(interpolation=None)
        parser.read(cfg_path, encoding='utf-8')
        for section in parser.sections():
            for key, value in parser[section].items():
                key_upper = key.upper()

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

                globals()[key_upper] = final_val
