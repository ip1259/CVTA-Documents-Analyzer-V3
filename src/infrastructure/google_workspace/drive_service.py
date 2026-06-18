import asyncio
from pathlib import Path
from typing import List, Dict, Optional, Callable, Awaitable
from googleapiclient.http import MediaFileUpload
from src.infrastructure.logger import info, error, warning, debug
from src.infrastructure.google_workspace import GoogleServiceAccount


class GoogleDriveService:
    """Google Drive 檔案操作服務 (支援非同步非阻塞呼叫)"""

    def __init__(self, google_account_service: GoogleServiceAccount):
        """
        初始化 Drive 服務
        :param google_account_service: 已認證的 GoogleServiceAccount 實例
        """
        self._gs = google_account_service
        self._service = google_account_service.drive_service

    async def find_folder_id(self, folder_name: str) -> Optional[str]:
        """
        搜尋指定名稱的資料夾 ID
        """
        if not self._gs.authenticated:
            return None

        def _sync_find():
            query = (
                f"name = '{folder_name}' and "
                f"mimeType = 'application/vnd.google-apps.folder' and "
                f"trashed = false"
            )
            response = self._service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)',
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
            files = response.get('files', [])
            return files[0]['id'] if files else None

        try:
            info(f"正在搜尋資料夾：{folder_name}")
            return await asyncio.to_thread(_sync_find)
        except Exception as e:
            error(f"搜尋資料夾 '{folder_name}' 失敗: {e}", exc_info=True)
            return None

    async def find_file_id(self, file_name: str, folder_id: str) -> Optional[str]:
        """
        搜尋指定資料夾下的特定檔案 ID
        """
        if not self._gs.authenticated:
            return None

        def _sync_find():
            query = f"name = '{file_name}' and '{folder_id}' in parents and trashed = false"
            response = self._service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)',
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
            files = response.get('files', [])
            return files[0]['id'] if files else None

        try:
            debug(f"正在資料夾 {folder_id} 中搜尋檔案：{file_name}")
            return await asyncio.to_thread(_sync_find)
        except Exception as e:
            error(f"搜尋檔案 '{file_name}' 失敗: {e}")
            return None

    async def upload_files(
        self,
        file_paths: List[str],
        folder_id: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        conflict_solve_callback: Optional[Callable[[
            str], Awaitable[bool]]] = None
    ) -> List[Dict[str, str]]:
        """
        批量上傳檔案到指定資料夾
        :param progress_callback: 進度回呼函式，接收 (已完成數, 總總數, 當前檔名)
        :param conflict_solve_callback: 衝突解決回呼，接收檔名並回傳是否覆蓋 (True: 覆蓋, False: 沿用現有 ID)
        :return: 包含成功上傳檔案 ID 的列表 [{"name": "...", "id": "..."}]
        """
        if not self._gs.authenticated or not self._gs.upload_drive_service:
            warning("Google API 未認證或上傳服務未就緒，無法上傳檔案")
            return []

        async def _upload_single(file_path: str):
            path_obj = Path(file_path)
            if not path_obj.exists():
                warning(f"檔案不存在，跳過上傳: {file_path}")
                return None

            # 1. 檢查檔案是否存在
            existing_id = await self.find_file_id(path_obj.name, folder_id)
            should_update = False

            if existing_id:
                if conflict_solve_callback:
                    # 呼叫 UI 回呼詢問使用者
                    should_update = await conflict_solve_callback(path_obj.name)

                if not should_update:
                    info(
                        f"檔案 '{path_obj.name}' 已存在且使用者選擇不覆蓋，沿用現有 ID: {existing_id}")
                    return {'id': existing_id, 'name': path_obj.name}

            def _sync_perform():
                media = MediaFileUpload(str(path_obj), resumable=True)
                if should_update and existing_id:
                    # 執行更新 (Overwrite)
                    return self._gs.upload_drive_service.files().update(
                        fileId=existing_id,
                        media_body=media,
                        fields='id, name',
                        supportsAllDrives=True
                    ).execute()
                else:
                    # 執行建立 (New Upload)
                    file_metadata = {'name': path_obj.name,
                                     'parents': [folder_id]}
                    return self._gs.upload_drive_service.files().create(
                        body=file_metadata,
                        media_body=media,
                        fields='id, name',
                        supportsAllDrives=True
                    ).execute()

            try:
                action_str = "更新" if should_update else "上傳"
                info(f"開始{action_str}檔案: {path_obj.name}")
                result = await asyncio.to_thread(_sync_perform)
                info(f"{action_str}成功: {path_obj.name} (ID: {result.get('id')})")
                return result
            except Exception as e:
                error(f"{action_str}檔案 {path_obj.name} 失敗: {e}")
                return None

        completed_count = 0
        total_count = len(file_paths)

        async def _upload_and_report(file_path: str):
            """包裝單一上傳任務以觸發進度回報"""
            nonlocal completed_count
            result = await _upload_single(file_path)
            completed_count += 1
            if progress_callback:
                try:
                    # 觸發回呼，供 GUI 更新進度條
                    progress_callback(
                        completed_count, total_count, Path(file_path).name)
                except Exception as cb_err:
                    warning(f"進度回報回呼發生異常: {cb_err}")
            return result

        # 並行執行所有上傳任務
        tasks = [_upload_and_report(p) for p in file_paths]
        results = await asyncio.gather(*tasks)

        # 過濾掉失敗的 None 結果
        successful_uploads = [res for res in results if res is not None]
        info(f"批量上傳完成，成功 {len(successful_uploads)}/{len(file_paths)} 筆檔案")
        return successful_uploads
