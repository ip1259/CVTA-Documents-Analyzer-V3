# -*- coding: utf-8 -*-
"""整合流程測試：選檔 -> OCR -> Drive 上傳 -> Sheets 同步。"""

import sys
import asyncio
import os
from pathlib import Path
from tkinter import Tk, filedialog

# 將專案根目錄加入路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import (
    GOOGLE_KEY_PATH,
    GOOGLE_CLIENT_SECRET_PATH,
    GOOGLE_TOKEN_PATH
)
from src.domain.orchestrator import DocumentProcessor
from src.infrastructure.google_workspace.sheets_service import GoogleSheetsService
from src.infrastructure.google_workspace.drive_service import GoogleDriveService
from src.infrastructure.google_workspace import GoogleServiceAccount
from src.infrastructure.logger import info, error, warning


# 使用者指定的參數
TEST_SPREADSHEET_ID = "1XjVCfVRBD2oPKf7XgnDzA4sm7LLf0sC5XxjmytuHjQc"
TEST_SHEET_NAME = "115年度"
TARGET_FOLDER_NAME = "公文掃描"
PROMPTS_PATH = "config/prompts.json"


async def run_integration_test():
    info("=== 開始整合流程測試 ===")

    # 1. 初始化環境與服務
    gs = GoogleServiceAccount(
        service_account_path=str(GOOGLE_KEY_PATH),
        client_secret_path=str(GOOGLE_CLIENT_SECRET_PATH),
        token_path=str(GOOGLE_TOKEN_PATH)
    )
    if not gs.authenticated:
        error("Google API 認證失敗，測試終止。")
        return

    drive_service = GoogleDriveService(gs)
    sheets_service = GoogleSheetsService(
        gs, spreadsheet_id=TEST_SPREADSHEET_ID)
    processor = DocumentProcessor(prompts_path=PROMPTS_PATH)

    # 2. 模擬 UI 選檔
    root = Tk()
    root.withdraw()
    info("請選擇要測試的公文圖片檔案...")
    file_paths = filedialog.askopenfilenames(
        title="選取測試公文",
        filetypes=[("圖片檔案", "*.jpg *.jpeg *.png")]
    )
    if not file_paths:
        info("使用者取消選檔，測試結束。")
        return

    file_list = list(file_paths)

    # 3. 執行批次 OCR 解析
    info(f"正在執行 OCR 解析 (數量: {len(file_list)})...")
    batch_result = await processor.process_batch(file_list)

    if batch_result["success"] == 0:
        error("OCR 解析全部失敗，請檢查 Ollama 服務。")
        return

    # 4. 上傳檔案至 Google Drive 並取得 File ID
    info(f"正在尋找 Drive 目標資料夾: {TARGET_FOLDER_NAME}")
    folder_id = await drive_service.find_folder_id(TARGET_FOLDER_NAME)
    if not folder_id:
        error(f"找不到 Drive 資料夾 '{TARGET_FOLDER_NAME}'，無法進行後續同步測試。")
        return

    info(f"正在上傳檔案至 Google Drive...")
    upload_results = await drive_service.upload_files(
        file_list,
        folder_id,
        progress_callback=lambda c, t, n: info(f"上傳進度: {c}/{t} - {n}")
    )

    # 建立檔名與 Drive ID 的對照表
    file_id_map = {res['name']: res['id'] for res in upload_results}

    # 5. 格式化資料並同步至 Google Sheets
    info(f"正在準備寫入 Google Sheets (工作表: {TEST_SHEET_NAME})...")
    rows_to_append = []

    for r in batch_result["results"]:
        if not r.get("success"):
            continue

        filename = os.path.basename(r["image_path"])
        drive_id = file_id_map.get(filename, "")

        # 使用 SheetsService 的靜態方法格式化列資料
        formatted_row = GoogleSheetsService.format_sheet_row_with_id(
            r["csv_data"],
            drive_id
        )
        rows_to_append.append(formatted_row)

    if rows_to_append:
        try:
            sheets_service.append_values(
                rows_to_append, sheet_range=f"'{TEST_SHEET_NAME}'!A1")
            info(f"成功同步 {len(rows_to_append)} 筆資料至 Google Sheets。")
        except Exception as e:
            error(f"同步至 Google Sheets 失敗: {e}")
    else:
        warning("無有效資料可供同步。")

if __name__ == "__main__":
    asyncio.run(run_integration_test())
