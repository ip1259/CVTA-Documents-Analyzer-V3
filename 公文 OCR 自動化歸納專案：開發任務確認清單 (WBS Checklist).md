# **公文 OCR 自動化歸納專案：開發任務確認清單 (WBS Checklist)**

**版本：** V1.0  
**指導原則：** 規格驅動開發 (Specification-Driven Development, SDD)  
**專案策略：** 漸進式交付（Phase 1 MVP 優先消積木 $\\rightarrow$ Phase 2 完整雲端桌面版）

## **🟩 第一階段：MVP 快速消積木工具 (Phase 1\)**

**核心目標：** 幾天內建立核心工作流，利用 CLI 與原生檔案視窗（File Dialog）進行批次公文辨識，並將結構化資料穩定寫入本地 CSV，快速解決公文積壓痛點。

| 任務名稱 | 任務說明與核心成果物 | 驗收標準 (Acceptance Criteria) | 負責人 (Assigned To) | 狀態 (Status) |
| :---- | :---- | :---- | :---- | :---- |
| **1.1 基礎環境與專案骨架初始化** | 依據架構規格書建立目錄結構，並**實作根目錄 PROJECT_REFERENCE.md 導引文件模板**。確立「文件同步更新」之 Check-in 規範。 **成果物：** 專案骨架、PROJECT_REFERENCE.md、requirements.txt。 | 1\. 執行 pip install 無誤。 2\. 建立符合 SDD 規範的導引文件，並包含核心 Schema 摘要。 | 待指派 | 未開始 |
| **1.2 全域日誌系統 (Logger) 實作** | 於 src/infrastructure/logger.py 實現全域日誌配置。串接 Python 標準 logging 模組，配置終端機（Console）顏色高亮輸出，並封裝 app.log 與 error.log 的分層雙寫邏輯。需支援 DEBUG, INFO, WARNING, ERROR 四個日誌級別的配置。 **成果物：** 全域 Logger 模組。 | 1\. 測試呼叫 logger.warning()，終端機須噴出高亮黃字，且 logs/app.log 成功記錄。 2\. 發生 Exception 時呼叫 logger.error(..., exc\_info=True)，error.log 須完整捕獲 Traceback。 3\. 驗證 DEBUG, INFO, WARNING, ERROR 各級別日誌的輸出目的地與格式符合規格。 | 待指派 | 未開始 |
| **1.3 Ollama 多模態客戶端實作** | 於 src/infrastructure/ollama\_client.py 封裝與地端 Ollama API 的通訊。讀取 config/prompts.json 中的規格化 System Prompt，將公文圖檔進行 Base64 編碼，並在 Temperature \= 0.0 條件下發送請求。 **成果物：** Ollama 整合客戶端驅動代碼。 | 1\. 傳入單張真實公文圖片，能穩定接收到 Ollama 回傳的純 JSON 字串。 2\. 字串內嚴禁包含 \`\`\`json 等 Markdown 污染標記，確保 json.loads() 可直接解析。 | 待指派 | 未開始 |
| **1.4 日期校驗閘門 (Validator) 實作** | 於 src/domain/validator.py 實現資料合約驗證。解析並確保 7 個欄位型態正確（特別是 key\_points 必須為 Array），並執行資料型態調和，例如將 `key_points` 陣列轉換為逗號分隔字串，以符合儲存層要求。計算`{doc_date} - {current_date}`的絕對值天數差，執行 90 天安全窗口校驗演算法。 **成果物：** 資料合約與時間校驗核心邏輯。 | 1\. 傳入 2026-04-17（今日為 2026-06-11，約55天差），判定在 90 天安全閾值內，不報警告。 2\. 傳入故意幻覺寫錯的日期（如2016年），系統須正確識別並回傳 is\_valid=False 與警告訊息。 3\. 驗證器需能正確將 `key_points` 欄位從陣列型態轉換為逗號分隔字串。 | 待指派 | 未開始 |
| **1.5 本地儲存與 MVP 協調器整合** | 實作 local\_storage.py 以追加（Append）模式寫入 CSV 檔案。在 cli\_app.py 中整合 tkinter.filedialog 批次選檔視窗，並由 orchestrator.py 串接完整流水線。 **成果物：** 第一版可實際執行的 CLI 歸納工具。 | 1\. 執行 python src/ui/cli\_app.py 能正確彈出選檔視窗。 2\. 批次選取 3 張公文圖片，執行完畢後本地 data/output\_results/ 須自動生成一份完美對齊 7 個欄位的 CSV 報表。 3\. 產出的 CSV 報表中，`key_points` 欄位必須以逗號分隔的字串形式呈現。 | 待指派 | 未開始 |

## **🟦 第二階段：完整桌面應用程式與雲端自動化 (Phase 2\)**

**核心目標：** 導入精美跨平台 GUI，建立雙欄預覽對照介面，並完整整合 Google Workspace API，達成「本地編輯確認、雲端自動同步」的終極自動化生態系。

| 任務名稱 | 任務說明與核心成果物 | 驗收標準 (Acceptance Criteria) | 負責人 (Assigned To) | 狀態 (Status) |
| :---- | :---- | :---- | :---- | :---- |
| **2.1 Python \+ QML 雙欄對照 UI 開發** | 設計 src/ui/qml/main.qml 介面。左側建立 OCR 結構化欄位的可編輯表單（LineEdit/ComboBox），右側建立公文圖檔的即時預覽區域。透過 PySide6 訊號與槽（Signals & Slots）機制與後端進行動態資料綁定。 **成果物：** QML 介面與後端 View Model。 | 1\. 介面支援流暢的公文圖片縮放與拖拽預覽。 2\. 切換左側公文清單時，右側圖片與左側表單欄位必須同步重新整理，不得有延遲或死結。 | 待指派 | 未開始 |
| **2.2 Google Workspace API 整合驅動** | 於 src/infrastructure/google\_workspace/ 實作雲端同步客戶端。整合 google-api-python-client。實作自動建立雲端目錄、將公文圖檔上傳至 Google Drive，以及將確認後的結構化資料追加到指定 Google Sheets 的功能。需妥善處理 API 權限控管、網路超時與例外重試機制。 **成果物：** Google 雲端整合服務驅動。 | 1\. 點擊 UI 「同步雲端」按鈕後，Google Drive 必須出現該公文圖檔。 2\. 指定的 Google Sheets 尾端必須自動追加一列對齊欄位的公文 OCR 結構化數據。 3\. 系統需具備處理 Google API 認證失效、連線逾時等錯誤的能力，並透過日誌系統記錄相關異常。 | 待指派 | 未開始 |
| **2.3 品質保證 (QA) 與 95% 準確度調優** | 將 30\~50 份涵蓋不同機關、排版與雜訊（低解析度、傾斜、蓋章遮擋）的真實公文放入 tests/golden\_dataset/。撰寫自動化基準測試腳本（Benchmark），微調 System Prompt 與大模型參數。 **成果物：** 自動化測試腳本與品質驗收報告。 | 1\. 基準測試腳本批次跑完黃金數據集，綜合欄位識別完全正確率（Accuracy Rate）必須穩定達到 **95%** 以上。 | 待指派 | 未開始 |
