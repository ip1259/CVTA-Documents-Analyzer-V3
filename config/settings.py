# -*- coding: utf-8 -*-
"""CVTA 全域設定檔 - 系統參數與環境變數配置"""

import os
import configparser
from pathlib import Path

# 定義目錄結構
CONFIG_DIR = Path(__file__).parent.resolve()
BASE_DIR = CONFIG_DIR.parent

# --- 1. 定義系統預設值 (程式碼內的基準設定) ---
# Ollama 多模態模型設定
OLLAMA_HOST = "http://IP:11434"
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


# --- 2. 自動建立預設 config 檔 (若不存在任何 .cfg) ---
def _ensure_default_config():
    """若 config 目錄下沒有任何 .cfg 檔案，則建立一個預設的 settings.cfg"""
    cfg_files = [f for f in os.listdir(CONFIG_DIR) if f.endswith('.cfg')]
    if not cfg_files:
        default_cfg_path = CONFIG_DIR / "settings.cfg"
        config = configparser.ConfigParser(interpolation=None)
        config['Ollama'] = {
            'OLLAMA_HOST': OLLAMA_HOST,
            'OLLAMA_MODEL': OLLAMA_MODEL
        }
        config['System'] = {
            'SYSTEM_NAME': SYSTEM_NAME,
            'VERSION': VERSION,
            'SYSTEM_LANGUAGE': SYSTEM_LANGUAGE
        }
        config['Rules'] = {
            'DATE_VALIDATION_DAYS': str(DATE_VALIDATION_DAYS)
        }
        config['Logging'] = {
            'LOG_LEVEL': LOG_LEVEL,
            'LOG_FORMAT': LOG_FORMAT,
            'LOG_DIR': LOG_DIR
        }
        config['Storage'] = {
            'DATA_DIR': DATA_DIR,
            'INPUT_DIR': INPUT_DIR,
            'OUTPUT_DIR': OUTPUT_DIR
        }
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
