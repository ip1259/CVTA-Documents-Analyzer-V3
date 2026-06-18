# CVTA-Documents-Analyzer 專案參考文檔

**版本：** V1.1  
**架構：** 模組化設計、Phase 1 MVP → Phase 2 完整桌面版  
**指導原則：** 規格驅動開發 (SDD)

## 🏗️ 系統架構

```
cvta-documents-analyzer-v3/
├── src/
│   ├── infrastructure/
│   │   ├── logger.py             # 全域日誌系統
│   │   ├── ollama_client.py      # Ollama API 客戶端
│   │   ├── local_storage.py      # 本地 CSV 儲存
│   │   └── google_workspace/     # Google Drive/Sheets API
│   │       ├── __init__.py       # 服務帳戶認證管理
│   │       ├── drive_service.py  # Drive 檔案操作（已實作）
│   │       └── sheets_service.py # Sheets 資料寫入（需補實作）
│   ├── domain/
│   │   ├── validator.py          # 資料校驗閘門
│   │   ├── orchestrator.py       # 流程協調器
│   │   └── __init__.py
│   └── ui/
│       ├── cli_app.py            # CLI 介面
│       └── main_qml.py           # QML GUI (Phase 2)
│       └── __init__.py
├── config/
│   └── prompts.json              # System Prompt 規格
├── logs/                          # 日誌輸出
├── data/                         # 資料儲存
│   └── output_results/           # CSV 產出目錄
├── tests/                        # 測試腳本
│   └── golden_dataset/           # 黃金測試資料
├── pyproject.toml
└── PROJECT_REFERENCE.md
```

## 📊 核心資料結構（Data Schema）

### 公文 OCR 輸出合約
```json
doc_date:         string   (ISO-8601 YYYY-MM-DD, 民國→西元自動轉換)
doc_category:     string   (字別字串，例："中分署訓")
doc_number:       string   (純數字，例："1152301262")
doc_from:         string   (機關全銜)
case_officer:     string   (承辦人姓名)
related_class:    string   (班別/專案)
key_points:       string[] (關鍵標籤陣列，CSV 時以逗號串接)
```

### 日期校驗閘門 (90 天規則)
- 計算：`abs(doc_date - current_date)`
- 閾值：**90 天**
- 超過閾值 → 輸出 `⚠️ WARNING` 並標示「需人工覆核」

## 🔧 核心模組說明

### Infrastructure Layer
| 模組 | 職責 | 完成度 |
|------|------|--------|
| `logger` | 雙寫 (Console 高亮 + 檔案日誌), 支援 DEBUG/INFO/WARNING/ERROR | ✅ 100% |
| `ollama_client` | 讀取 prompts.json, Base64 編碼圖片，Temperature=0.0 發送請求 | ✅ 100% |
| `local_storage` | Append 模式寫入 CSV，確保 key_points 為逗號分隔字串 | ✅ 100% |
| `orchestrator` | 串接完整流水線：選檔→OCR→校驗→儲存 | ✅ 100% |
| `google_workspace.__init__` | 雙憑證系統 (Service Account + OAuth 2.0) | ✅ 100% |
| `google_workspace.drive_service` | 搜尋、上傳、**重複檢查與覆蓋處理邏輯** | 🟡 70% |
| `google_workspace.sheets_service` | 寫入 Google Sheets | 🔴 **未完工** |

### Domain Layer
| 模組 | 職責 | 完成度 |
|------|------|--------|
| `validator` | 7 欄位型態校驗，日期 90 天閘門，陣列→字串轉換 | ✅ 100% |
| `orchestrator` | 批次處理 + 結果彙整 | ✅ 100% |

### UI Layer
| 模組 | 職責 | 完成度 |
|------|------|--------|
| `cli_app` | Tkinter File Dialog + 批次選檔 | ✅ 100% |
| `main_qml` | 雙欄 UI(左表單 + 右預覽，Phase 2) | 🔴 **未開始** |

## 🚀 開發順序

### Phase 1.1 基礎環境與專案架構（已完成 ✅）
### Phase 1.2 全域日誌系統（已完成 ✅）
### Phase 1.3 Ollama 客戶端（已完成 ✅）
### Phase 1.4 校驗閘門（已完成 ✅）
### Phase 1.5 本地儲存與 CLI 整合（已完成 ✅）

### Phase 2.1 Python+QML 雙欄對照 UI（未開始 🔴）
### Phase 2.2 Google Workspace API 整合（部分完成 🟡）
- ✅ Drive CRUD 已實作
- ⚠️ Sheets write 缺少 `sheets_service.py`
- 🔴 需要與 UI 整合
### Phase 2.3 QA 與調優（未開始 🔴）

## ✅ 完成狀態表

| 任務編號 | 任務名稱 | 狀態 | 完成度 | 備註 |
|----------|----------|------|--------|------|
| 1.1 | 基礎環境與專案架構 | ✅ | 100% | PROJECT_REFERENCE.md 已建立 |
| 1.2 | 全域日誌系統 | ✅ | 100% | Logger 雙寫測試通過 |
| 1.3 | Ollama 客戶端 | ✅ | 100% | Base64 編碼 + Markdown 清理完成 |
| 1.4 | 日期校驗閘門 | ✅ | 100% | 90 天閾值 + key_points 陣列→字串轉換 |
| 1.5 | 本地儲存與 CLI 整合 | ✅ | 100% | CSV Append 模式完成 |
| 2.1 | Python+QML 雙欄對照 UI | 🔴 | 0% | 未開始 |
| 2.2.1 | Google Drive API - 搜尋 & 上傳 | ✅ | 100% | 含進度回呼機制 |
| 2.2.2 | Google Sheets API - 寫入資料 | 🔴 | 0% | 需實作 sheets_service.py |
| 2.2.3 | 雲端整合 UI 整合 | 🔴 | 0% | 未開始 |
| 2.3 | QA 與自動化測試 | 🔴 | 0% | 需撰寫 Benchmark 腳本 |

---

**⚠️ 待辦：**
1. 實作 `src/infrastructure/google_workspace/sheets_service.py`
2. 開發 Phase 2.1 GUI 介面 (PySide6 + QML)
3. 整合 Google API 登入流程至 UI

---

*最後更新：2026-06-17*
