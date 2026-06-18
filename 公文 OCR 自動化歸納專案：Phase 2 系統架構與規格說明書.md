# **公文 OCR 自動化歸納專案：Phase 2 系統架構與規格說明書**

**版本：** V1.0  
**指導原則：** 規格驅動開發 (Specification-Driven Development, SDD)  
**階段目標：** 完整桌面應用程式與雲端自動化同步整合

## **1\. 階段概述 (Phase 2 Overview)**

本文件承接「專案憲章 (Project Charter)」，聚焦於 **Phase 2：完整桌面應用程式** 的詳細系統架構、目錄結構、日誌系統規格以及核心提示詞（System Prompt）合約。本階段的核心價值在於提供精美的跨平台圖形介面（GUI），並整合 Google Workspace API，建構端到端的自動化公文歸納生態系。

## **2\. 系統分層架構藍圖 (System Architecture Layers)**

為了確保系統的可維護性、可測試性，並嚴格遵循單一職責原則（SRP），Phase 2 採用高度解耦的四層架構設計：

* **表現層 (Presentation Layer / UI)：** 採用 Python \+ QML (PySide6/PyQt6) 實現。核心為「雙欄對照 UI」，左側提供 OCR 結構化欄位的即時預覽與編輯表單，右側提供公文原始圖檔的縮放預覽，兩者具備高動態綁定特性。  
* **業務邏輯層 (Domain / Business Logic Layer)：**  
  * Orchestrator (工作流協調器)：調度影像讀取、LLM 解析、資料驗證、本地備份及雲端同步的完整流水線（Pipeline）。  
  * Validator (校驗閘門)：執行 90 天時間窗口驗證，並在資料進入儲存層前進行型態調和（如陣列轉逗號字串）。  
* **基礎設施與驅動層 (Infrastructure / Drivers Layer)：**  
  * Ollama Client：封裝多模態大模型通訊，設定 Temperature \= 0.0，確保結構化輸出。  
  * Logger：全域日誌配置器，負責分層雙寫。  
  * Google Workspace Connector：整合 Google Drive 與 Sheets API，控管權限、網路超時與例外重試，並包含上傳前的檔案重複檢查與衝突解決（覆蓋/跳過）邏輯。

## **3\. 完整專案目錄結構規格 (Directory Layout Specification)**

本結構完全相容 Phase 1 的 MVP 實作，並具備 Phase 2 所需的所有雲端與 GUI 擴充節點：  
`gov-ocr-project/`  
`├── PROJECT_REFERENCE.md        # 專案索引導引：紀錄函式摘要、Schema 與開發流導引`  
`│`  
`├── config/                     # 設定檔目錄`  
`│   ├── settings.py             # 全域變數（Ollama URL、Model Name、90天日期閾值等）`  
`│   └── prompts.json            # 集中管理多模態模型的 System Prompt 規格`  
`│`  
`├── src/                        # 核心原始碼目錄`  
`│   ├── __init__.py`  
`│   │`  
`│   ├── ui/                     # 表現層 (UI Layer)`  
`│   │   ├── __init__.py`  
`│   │   ├── cli_app.py          # Phase 1: MVP 命令列主程式`  
`│   │   ├── main_qml.py         # Phase 2: QML 應用程式啟動器`  
`│   │   └── qml/                # Phase 2: 存放 .qml 介面檔案與資源`  
`│   │`  
`│   ├── domain/                 # 業務邏輯層 (Business Logic Layer)`  
`│   │   ├── __init__.py`  
`│   │   ├── orchestrator.py     # 工作流協調器 (排程調度 OCR、校驗與儲存)`  
`│   │   └── validator.py        # 資料驗證器 (90天日期檢查、欄位型態確保)`  
`│   │`  
`│   └── infrastructure/         # 基礎設施層 (Infrastructure Layer)`  
`│       ├── __init__.py`  
`│       ├── logger.py           # 全域日誌配置器 (封裝 Python logging)`  
`│       ├── ollama_client.py    # Ollama API 聯絡客戶端 (多模態模型驅動)`  
`│       ├── local_storage.py    # 本地端檔案讀寫 (JSON / CSV)`  
`│       └── google_workspace/   # Phase 2: Google API 整合模組`  
`│           ├── __init__.py`  
`│           ├── drive_service.py # 自動上傳掃描圖檔至 Google Drive`  
`│           └── sheets_service.py # 自動追加 OCR 數據至 Google Sheets`  
`│`  
`├── tests/                      # 品質保證與測試目錄`  
`│   ├── __init__.py`  
`│   ├── golden_dataset/         # 存放 30~50 張黃金基準測試公文圖檔`  
`│   ├── test_validator.py       # 驗證器單元測試`  
`│   └── test_pipeline.py        # 整合測試`  
`│`  
`├── logs/                       # 執行時期日誌檔案存放區 (.gitignore 排除)`  
`│   ├── app.log                 # 追蹤一般流程、除錯與警告訊息`  
`│   └── error.log               # 專門記錄異常與報錯 (Exception Rollback)`  
`│`  
`├── data/                       # 執行時期的本地資料存放區 (.gitignore 排除)`  
`│   ├── input_scans/            # 待處理的公文掃描檔`  
`│   └── output_results/         # 產出的 JSON 或 CSV 檔案`  
`│`  
`├── pyproject.toml              # uv 專案設定與依賴清單 (PySide6, requests, openpyxl, etc.)`  
`├── uv.lock                     # uv 自動生成的依賴鎖定檔`  
`└── .gitignore                  # 排除金鑰、日誌與臨時暫存檔`

## **4\. 全域日誌系統規格 (Logging System Contract)**

為提升系統的可觀測性，日誌系統採終端機與檔案雙軌輸出，定義四個嚴格日誌級別：

| 日誌級別 | 業務觸發時機 | 輸出目的地 |
| :---- | :---- | :---- |
| **DEBUG** | Ollama 傳回的原始 JSON 字串、圖檔載入的二進位狀態。 | 僅記錄於 logs/app.log，終端機不顯示。 |
| **INFO** | 使用者選取檔案、工作流啟動/結束、成功寫入本地 CSV 或成功同步至 Google 雲端。 | logs/app.log 與終端機（Console）同步顯示。 |
| **WARNING** | **Validator 判定公文日期與今日超過 90 天**、模型回傳欄位有缺失但可透過預設值補齊。 | logs/app.log，終端機以 **高亮黃字** 顯示，提示人工覆核。 |
| **ERROR** | Ollama 服務未啟動、圖檔損毀、Google Workspace API 連線逾時或認證失效。 | **雙寫**至 app.log 與 error.log（含 Traceback），終端機以 **紅字** 噴出。 |

## **5\. 核心多模態 Prompt 規格合約 (System Prompt Contract)**

存放於 config/prompts.json，在 Temperature \= 0.0 條件下執行，確保模型 100% 聽話且不產生 Markdown 污染：  
`你是一個專業的台灣公文 OCR 語意解析專家。你的任務是精準閱讀公文圖片，擷取關鍵資訊，並嚴格以結構化的純 JSON 格式輸出。`

`【輸出格式約束】`  
````1. 必須只輸出一個合法的 JSON 物件，嚴禁包含任何 Markdown 標記（如 ```json）、前後導言或解釋性文字。````  
`2. 除了 JSON 的 Key 必須保持指定的英文名稱外，Value 中的所有中文必須使用【繁體中文】輸出。`  
`3. 若某欄位在公文中完全未提及或找不到，請依據欄位定義回傳預設值（"" 或 []），嚴禁缺失該 Key。`

`【資料欄位與轉換規則規格】`  
`- doc_date (String): 發文日期。格式統一為 ISO-8601 標準 "YYYY-MM-DD"。公文上若為中華民國曆（民國年），必須自動加 1911 轉換為西元年（例如：民國 115 年 04 月 17 日 -> "2026-04-17"）。`  
`- doc_category (String): 發文字別。公文文號結構通常為「[字別]字第[文號]號」，此欄位僅擷取「字別」部分（即「字」字之前的所有文字，例如："中分署訓"）。`  
`- doc_number (String): 發文文號。公文文號結構通常為「[字別]字第[文號]號」，此欄位僅擷取「文號」部分（即「第」與「號」之間的數字或編號字串，例如："1152301262"）。`  
`- doc_from (String): 發文機關全銜。通常以大標題位於公文頂部。僅擷取機關名稱，必須捨棄結尾的文體後綴（如 "函"、"書函"）。`  
`- case_officer (String): 承辦人/聯絡人姓名。若公文中未提及，預設回傳 ""。`  
`- related_class (String): 相關班級或專案名稱。系統須從主旨或說明段落中提煉出特定班級名稱（例如："多媒體設計與AI應用創作班"）。若無相關班級，預設回傳 "無"。`  
`- key_points (Array of Strings): 公文核心重點關鍵字清單。請根據公文的主旨與說明，提煉出 2 到 5 個核心主題標籤。格式必須為字串陣列（例如：["115年度商業類", "職前訓練勞務採購案"]）。`

`【範例輸出 (Example)】`  
`{`  
    `"doc_date": "2026-04-17",`  
    `"doc_category": "中分署訓",`  
    `"doc_number": "1152301262",`  
    `"doc_from": "勞動部勞動力發展署中彰投分署",`  
    `"case_officer": "王慶華",`  
    `"related_class": "多媒體設計與AI應用創作班",`  
    `"key_points": ["115年度商業類", "職前訓練勞務採購案", "職業訓練生活津貼"]`  
`}`