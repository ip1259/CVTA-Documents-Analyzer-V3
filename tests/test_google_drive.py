# -*- coding: utf-8 -*-
import sys
import os
import asyncio
from pathlib import Path
from tkinter import filedialog, Tk, messagebox

# 將專案根目錄加入路徑以確保能載入 config 與 src
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 路徑設定好後，再匯入專案模組
from src.infrastructure.logger import info, error, warning
from src.infrastructure.google_workspace import GoogleServiceAccount
from src.infrastructure.google_workspace.drive_service import GoogleDriveService
from config.settings import GOOGLE_KEY_PATH, GOOGLE_CLIENT_SECRET_PATH, GOOGLE_TOKEN_PATH


def test_list_google_drive_files():
    """驗證 Google Drive 功能：搜尋特定資料夾並列出前 10 個檔案"""

    info("開始 Google Drive API 功能測試...")

    # 1. 初始化服務帳戶
    # 這裡會讀取 config/settings.py 中定義的 google_key.json
    gs = GoogleServiceAccount(
        service_account_path=str(GOOGLE_KEY_PATH),
        client_secret_path=str(GOOGLE_CLIENT_SECRET_PATH),
        token_path=str(GOOGLE_TOKEN_PATH)
    )

    if not gs.authenticated:
        error("Google API 認證失敗，請檢查 google_key.json 是否存在於 config 目錄下。")
        return

    info(f"正在使用服務帳戶：{gs.service_account_email}")
    info("請確保已在 Google Drive 中將資料夾『共享』給上述 Email。")

    drive = gs.drive_service
    folder_name = "公文掃描"

    try:
        # 2. 尋找名稱為 "公文掃描" 的資料夾 ID
        query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        response = drive.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)',
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        folders = response.get('files', [])

        if not folders:
            warning(f"在雲端硬碟中找不到名為 '{folder_name}' 的資料夾。")
            return

        folder_id = folders[0]['id']
        info(f"成功找到資料夾：{folder_name} (ID: {folder_id})")

        # 3. 列出該資料夾下的前 10 個檔案
        file_query = f"'{folder_id}' in parents and trashed = false"
        file_response = drive.files().list(
            q=file_query,
            pageSize=10,
            fields="nextPageToken, files(id, name, mimeType, createdTime)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()

        files = file_response.get('files', [])

        if not files:
            info(f"資料夾 '{folder_name}' 內目前沒有檔案。")
        else:
            info(f"成功取得資料夾內的前 {len(files)} 個檔案：")
            for i, file in enumerate(files, 1):
                print(
                    f"{i:02d}. 名稱: {file['name']} | ID: {file['id']} | 類型: {file['mimeType']}")

    except Exception as e:
        error(f"測試過程中發生異常：{e}", exc_info=True)


async def test_google_drive_service_wrapper():
    """驗證 GoogleDriveService 包裝類別的功能"""
    info("開始 GoogleDriveService 非同步包裝類別測試...")

    gs = GoogleServiceAccount(
        service_account_path=str(GOOGLE_KEY_PATH),
        client_secret_path=str(GOOGLE_CLIENT_SECRET_PATH),
        token_path=str(GOOGLE_TOKEN_PATH)
    )
    if not gs.authenticated:
        error("Google API 認證失敗。")
        return

    drive_service = GoogleDriveService(gs)

    # 1. 測試搜尋資料夾
    folder_name = "公文掃描"
    fid = await drive_service.find_folder_id(folder_name)
    if fid:
        info(f"成功找到資料夾 '{folder_name}' ID: {fid}")

        # 2. 測試搜尋檔案 (以特定檔名為例)
        target_file = "115090_0001.jpg"
        file_id = await drive_service.find_file_id(target_file, fid)
        if file_id:
            info(f"成功找到檔案 '{target_file}' ID: {file_id}")
        else:
            warning(f"在資料夾中找不到檔案 '{target_file}'")
    else:
        warning(f"找不到資料夾 '{folder_name}'")


async def test_google_drive_upload():
    """測試檔案上傳功能，使用 filedialog 選擇檔案"""
    info("開始 Google Drive 上傳測試...")

    # 讓使用者選擇檔案 (可多選)
    file_paths = filedialog.askopenfilenames(title="請選擇要測試上傳的檔案")
    if not file_paths:
        info("使用者取消選取，跳過上傳測試。")
        return

    gs = GoogleServiceAccount(
        service_account_path=str(GOOGLE_KEY_PATH),
        client_secret_path=str(GOOGLE_CLIENT_SECRET_PATH),
        token_path=str(GOOGLE_TOKEN_PATH)
    )
    if not gs.authenticated:
        error("Google API 認證失敗。")
        return

    drive_service = GoogleDriveService(gs)
    folder_name = "公文掃描"

    # 1. 搜尋目標資料夾
    fid = await drive_service.find_folder_id(folder_name)
    if not fid:
        error(f"找不到資料夾 '{folder_name}'，無法進行上傳測試。")
        return
        
    async def conflict_handler(filename: str) -> bool:
        """
        處理檔案衝突的回呼函式
        使用 tkinter messagebox 詢問使用者
        """
        return messagebox.askyesno(
            "檔案衝突",
            f"雲端資料夾中已存在檔案：\n'{filename}'\n\n是否要覆蓋既有檔案？\n(選「否」則會保留舊檔並沿用其 ID)"
        )

    # 2. 呼叫批量上傳 (支援進度回報)
    info(f"準備上傳 {len(file_paths)} 個檔案至 '{folder_name}'...")
    results = await drive_service.upload_files(
        list(file_paths),
        fid,
        progress_callback=lambda cur, tot, name: info(f"上傳進度：{cur}/{tot} - {name}"),
        conflict_solve_callback=conflict_handler
    )
    info(f"上傳測試完成，成功上傳 {len(results)} 筆檔案。")


if __name__ == "__main__":
    # 初始化 Tkinter 並隱藏主視窗，確保 UI 控制項在主執行緒中初始化
    tk_root = Tk()
    tk_root.withdraw()

    # 1. 執行同步 API 測試
    test_list_google_drive_files()

    # 2. 執行所有非同步測試案例
    async def run_async_tests():
        print("\n" + "="*50 + "\n")
        await test_google_drive_service_wrapper()
        print("\n" + "-"*50 + "\n")
        await test_google_drive_upload()

    asyncio.run(run_async_tests())
