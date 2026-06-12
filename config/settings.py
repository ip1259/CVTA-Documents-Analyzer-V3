# -*- coding: utf-8 -*-
"""CVTA 全域設定檔 - 系統參數與環境變數配置"""

import os
import configparser

# 計算工作目錄 (與主程式同目錄，兼容打包後架構)
WORK_DIR = os.path.dirname(os.path.abspath(__file__))

# 載入工作目錄下的.cfg 設定檔
_config = {}
for cfg_file in sorted(os.listdir(WORK_DIR), key=str.lower):
    if cfg_file.endswith('.cfg'):
        cfg_path = os.path.join(WORK_DIR, cfg_file)
        config = configparser.ConfigParser()
        config.read(cfg_path, encoding='utf-8')
        for section in config.sections():
            for key, value in config[section].items():
                try:
                    if value.lower() == 'true':
                        _config[key] = True
                    elif value.lower() == 'false':
                        _config[key] = False
                    elif '.' not in value and int(value):
                        _config[key] = int(value)
                    elif '.' in value and float(value):
                        _config[key] = float(value)
                    else:
                        _config[key] = value
                except (ValueError, TypeError):
                    pass

# 應用 cfg 設定到全域變數
for key, value in _config.items():
    globals()[key] = value

# Ollama 多模態模型設定
OLLAMA_HOST = "http://<Your IP>:11434"
OLLAMA_MODEL = "qwen3.5:9b"

# 系統參數
SYSTEM_NAME = "公文 OCR 自動化歸納系統"
VERSION = "3.0.0"

# 業務規則：日期校驗閾值 (天)
DATE_VALIDATION_DAYS = 90

# 日誌設定
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DIR = "logs"

# 資料儲存設定
DATA_DIR = "data"
INPUT_DIR = "input_scans"
OUTPUT_DIR = "output_results"

# 系統語言設定
SYSTEM_LANGUAGE = "zh-TW"