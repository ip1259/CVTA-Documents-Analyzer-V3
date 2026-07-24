# CVTA Documents Analyzer V3

公文圖片 OCR、欄位驗證、本地儲存及 Google Workspace 同步工具。

## 環境需求

- Python 3.13 以上
- uv
- Ollama
- 選用：Google Workspace API 認證

## 安裝

```powershell
uv sync
```

## 啟動 GUI

```powershell
uv run python -m src.luncher
```

Google 認證不可用時，GUI 及本地新增、分析、CSV、JSON 功能仍可使用；
執行 Drive 或 Sheets 功能時才會顯示認證錯誤。

## 執行 CLI

```powershell
uv run python -m src.domain.orchestrator --images <image1> <image2>
```

輸出額外複製格式 CSV：

```powershell
uv run python -m src.domain.orchestrator --images <image1> --extra_output
```

查看參數：

```powershell
uv run python -m src.domain.orchestrator --help
```

## 執行測試

```powershell
uv run python -m unittest discover -s tests -v
```

Google Drive 與 Sheets 的自動測試使用 mock，不需要實際憑證，也不會修改
雲端資料。發布前應另以測試帳號及測試資料夾執行手動整合測試。

## 設定

主要設定位於：

- `src/config/settings.py`
- `src/config/settings.cfg`
- `src/config/prompts.json`

標準執行方式為從專案根目錄使用 `python -m src...`。專案內部統一使用
`src.*` 絕對匯入，不需手動設定 `PYTHONPATH` 或修改 `sys.path`。
