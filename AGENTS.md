# CVTA Documents Analyzer - 開發指南

## 關於程式碼搜尋的嚴格規範
1. 嚴禁在終端機（execute_command）中呼叫 `grep`、`egrep` 或 `findstr` 指令來搜尋程式碼。
2. 當你需要跨檔案搜尋特定的關鍵字、函數或變數時，必須且只能使用內建的 `search_files` 工具。
3. 如果內建工具沒有找到任何結果，請直接在 `<think>` 中記錄「未找到相關程式碼」，並嘗試更換關鍵字，絕對不要退回終端機去執行 `grep`。

## 環境要求

- Python >= 3.13
- uv 套件管理工具（用於依賴安裝）
- Ollama 服務（本地多模態模型）
- 可選：Google Workspace API 認證（用於雲端同步）

## 快速啟動

```bash
# 安裝依賴
uv sync

# 執行 CLI（選取圖片批次處理）
python -m uv run src/ui/cli_app.py

# 使用 tests/golden_dataset/ 中的測試圖片測試
python -m uv run src/domain/orchestrator.py --images tests/golden_dataset/*.jpg
```

## 系統架構

```
src/                            # 核心程式碼
├── ui/                         # 表現層
│   ├── cli_app.py              # CLI 入口（批次選檔）
│   └── main_qml.py             # QML GUI（Phase 2）
├── domain/                     # 業務邏輯
│   ├── orchestrator.py         # 流程協調器（OCR→驗證→儲存）
│   └── validator.py            # 資料驗證器（90 天日期閾值、欄位型別檢查）
└── infrastructure/             # 基礎設施
    ├── logger.py               # 日誌（logs/app.log + logs/error.log）
    ├── ollama_client.py        # Ollama 多模態 API
    ├── local_storage.py        # 本地檔案（CSV/JSON）
    └── google_workspace/       # Google Drive/Sheets API（Phase 2）
```

## 執行步驟

### 1. 處理單張圖片
```python
from src.domain.orchestrator import DocumentProcessor

processor = DocumentProcessor("config/prompts.json")
result = asyncio.run(processor.process_single("path/to/image.jpg"))
```

### 2. 批次處理（含 GUI 選檔）
```python
from src.ui.cli_app import main
main()
```

### 3. 執行測試
```bash
# 驗證器測試
uv run python tests/test_validator.py

# 整合管道測試
uv run python tests/test_pipeline.py

# Google Drive 測試
uv run python tests/test_google_drive.py
```

## 關鍵規範

### 模型輸出（Ollama）
- **Temperature = 0.0**：確保穩定結構化輸出
- **純 JSON 格式**：禁止 Markdown 標記（```json）、前後導言
- **Temperature 參數**：`top_p: 0.9`, `num_predict: 4096`

### 欄位規範（config/prompts.json）
| 欄位              | 規範                                                                 |
|-------------------|----------------------------------------------------------------------|
| `doc_date`        | ISO-8601 格式 (`YYYY-MM-DD`)；民國 X11 年 → X11 + 1911              |
| `doc_category`    | 字別（例如："中分署訓"）                                             |
| `doc_number`      | 文號純數字（例如："1152301262"）                                    |
| `doc_from`        | 發文機關全銜，移除結尾（如 "函"、"書函"）                          |
| `key_points`      | 字串陣列，2~5 個關鍵字                                              |
| `*預設*`          | 欄位缺失時回傳 `""` 或 `[]`，不可省略該 Key                        |

### 資料驗證（validator.py）
- **90 天日期閾值**：超過 90 天會標記為 WARNING（WARNING 級別寫入 logs/app.log）
- **必填欄位檢查**：7 個欄位缺一不可（缺少即標記為 ERROR）
- **key_points 型態調和**：陣列→逗號分隔字串（供 CSV 儲存）

### 日誌系統
| 級別   | 輸出位置                              |
|--------|---------------------------------------|
| DEBUG  | logs/app.log（僅此，終端機不顯示）   |
| INFO   | logs/app.log + 終端機                 |
| WARNING| logs/app.log + 終端機（黃色高亮）     |
| ERROR  | logs/app.log + logs/error.log（紅色）+ Traceback |

## 檔案路徑

| 用途                | 路徑                                            |
|---------------------|-------------------------------------------------|
| 待處理掃描檔        | `data/input_scans/`                             |
| 產出 CSV/JSON       | `data/output_results/`                          |
| 日誌檔案            | `logs/app.log`, `logs/error.log`               |
| 設定檔              | `config/prompts.json`, `config/settings.py`    |

## 常見問題

### Ollama 服務未啟動
```
python -m uv run src/ui/cli_app.py
```
- 終端機會顯示："請檢查 Ollama 服務是否運行"
- 解決方案：`ollama serve` 或檢查 Ollama URL 設定（config/settings.py）

### JSON 解析污染
ollama_client.py._parse_json_response() 自動移除 Markdown 標記：
- ````json` → `
- ` ```` → 移除

### 圖片格式支援
CLI 支援 `*.jpg`, `*.jpeg`, `*.png`（filedialog 預設過濾）

---
> 本規範以 config/settings.py, src/domain/orchestrator.py, src/domain/validator.py 為執行時真相來源。
