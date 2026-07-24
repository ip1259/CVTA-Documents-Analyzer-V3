# AI 服務確認修改計畫

## 一、修改目的

目前系統在文件分析時，會直接呼叫 Ollama `chat()` API，沒有在分析開始前確認：

- Ollama 服務是否可連線。
- 設定的 AI 模型是否已安裝且可使用。
- AI 服務是否在合理時間內回應。

本次修改將加入批次分析前的 AI 服務預檢（preflight check）。若檢查失敗，系統應立即停止該次分析並向使用者顯示明確原因，避免每份文件重複失敗或介面長時間等待。

## 二、修改範圍

### 1. Ollama Client

檔案：`src/infrastructure/ollama_client.py`

新增非破壞性的服務確認方法，例如：

```python
async def check_availability(self) -> tuple[bool, str]:
    ...
```

檢查內容：

1. 在指定 timeout 內連線至 `OLLAMA_HOST`。
2. 取得 Ollama 模型清單。
3. 確認 `OLLAMA_MODEL` 存在於模型清單。
4. 將例外轉換為可供 UI 顯示的錯誤訊息。

建議錯誤分類：

- `SERVICE_UNREACHABLE`：無法連線至 Ollama。
- `SERVICE_TIMEOUT`：服務回應逾時。
- `MODEL_NOT_FOUND`：指定模型尚未安裝。
- `SERVICE_ERROR`：其他 Ollama API 錯誤。

同時將目前 `AsyncClient(timeout=None)` 改為有限 timeout，避免請求無限等待。服務預檢與正式模型分析可分別設定較短與較長的 timeout。

### 2. 流程協調器

檔案：`src/domain/orchestrator.py`

在 `DocumentProcessor` 增加對外服務確認方法：

```python
async def check_ai_service(self) -> dict:
    ...
```

回傳格式建議：

```python
{
    "available": True,
    "error_code": "",
    "message": "",
    "model": "qwen3.5:9b"
}
```

`process_batch()` 必須在建立文件分析任務前執行一次檢查：

1. 檢查成功後才開始批次處理。
2. 檢查失敗時不呼叫任何文件的 `process_single()`。
3. 回傳批次級錯誤結果，供 CLI 或 GUI 顯示。

`process_single()` 保留原有例外處理，因為服務可能在預檢通過後才中斷。

### 3. GUI 分析流程

檔案：

- `src/ui/doc_controller.py`
- `src/infrastructure/data_storage.py`

在文件迴圈開始前執行一次 AI 服務確認：

1. 進度視窗顯示「正在確認 AI 服務可用性」。
2. 服務不可用時停止整批分析。
3. 不將每份文件分別標示為分析失敗。
4. 透過錯誤對話框顯示主機、模型及處理建議。

訊息範例：

- 「無法連線至 Ollama 服務，請確認服務已啟動及連線設定正確。」
- 「找不到模型 qwen3.5:9b，請先下載或修改模型設定。」
- 「Ollama 服務回應逾時，請稍後重試。」

### 4. CLI 分析流程

檔案：`src/domain/orchestrator.py`

CLI 在預檢失敗時：

1. 輸出明確的錯誤代碼及訊息。
2. 不開始文件處理。
3. 以非零狀態碼結束。

## 三、設定調整

檔案：`src/config/settings.py`

建議新增：

```python
OLLAMA_HEALTH_TIMEOUT = 5
OLLAMA_REQUEST_TIMEOUT = 300
```

設定值應可由 `settings.cfg` 覆寫。

## 四、測試計畫

### 單元測試

新增 Ollama client 服務確認測試，至少涵蓋：

- 服務可連線且模型存在。
- 服務無法連線。
- 服務回應逾時。
- 服務可連線但指定模型不存在。
- Ollama API 回傳非預期錯誤。
- 模型名稱含 tag 與不同回傳物件格式時仍能正確比對。

### 流程測試

- 預檢成功後才呼叫 `process_single()`。
- 預檢失敗時完全不送出文件分析請求。
- 批次分析只執行一次預檢。
- 預檢成功後，服務於處理途中失效時，仍由單份文件例外處理接手。
- GUI 收到預檢失敗結果時顯示錯誤且不寫入錯誤分析結果。
- CLI 預檢失敗時回傳非零狀態碼。

## 五、驗收標準

- Ollama 未啟動時，分析開始後能在設定的預檢 timeout 內提示錯誤。
- 指定模型未安裝時，在處理第一份圖片前提示模型不存在。
- 預檢失敗時，沒有任何 `chat()` 分析請求被送出。
- 一次批次分析只進行一次服務預檢。
- 服務可用時，原有單張與批次分析結果不受影響。
- 錯誤日誌保留技術細節，使用者介面顯示可理解且可採取行動的訊息。
- 所有新增及既有相關測試通過。

## 六、建議實作順序

1. 新增 timeout 設定。
2. 實作 `OllamaClient.check_availability()`。
3. 實作 `DocumentProcessor.check_ai_service()`。
4. 將預檢接入 CLI 與批次分析入口。
5. 將預檢接入 GUI 分析流程及錯誤對話框。
6. 新增單元測試與流程測試。
7. 執行完整測試並人工驗證 Ollama 停止、模型缺少及正常服務三種情境。

## 七、不包含於本次修改

- 自動啟動 Ollama 服務。
- 自動下載缺少的模型。
- 自動切換至其他 AI 模型。
- 修改 OCR prompt 或資料驗證規則。
