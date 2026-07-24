import asyncio
import threading
from pathlib import Path
from typing import Awaitable, Callable, Optional

from googleapiclient.http import MediaFileUpload

from src.infrastructure.google_workspace import (
    ConflictChoice,
    GoogleServiceAccount,
    UnauthenticatedError,
)
from src.infrastructure.logger import error, info, warning


class GoogleDriveService:
    """Google Drive file operations."""

    def __init__(self, google_account_service: GoogleServiceAccount):
        self._gs = google_account_service

    @property
    def _service(self):
        if not self._gs.authenticated:
            raise UnauthenticatedError()
        return self._gs.drive_service

    @property
    def _upload_service(self):
        if not self._gs.authenticated:
            raise UnauthenticatedError()
        return self._gs.upload_drive_service

    async def find_folder_id(self, folder_name: str) -> Optional[str]:
        if not self._gs.authenticated:
            raise UnauthenticatedError()

        def find():
            query = (
                f"name = '{folder_name}' and "
                "mimeType = 'application/vnd.google-apps.folder' and "
                "trashed = false"
            )
            response = self._service.files().list(
                q=query,
                spaces="drive",
                fields="files(id, name)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            ).execute()
            files = response.get("files", [])
            return files[0]["id"] if files else None

        return await asyncio.to_thread(find)

    async def find_file_id(
        self,
        file_name: str,
        folder_id: str
    ) -> Optional[str]:
        if not self._gs.authenticated:
            raise UnauthenticatedError()

        def find():
            query = (
                f"name = '{file_name}' and "
                f"'{folder_id}' in parents and trashed = false"
            )
            response = self._service.files().list(
                q=query,
                spaces="drive",
                fields="files(id, name)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            ).execute()
            files = response.get("files", [])
            return files[0]["id"] if files else None

        return await asyncio.to_thread(find)

    async def upload_files(
        self,
        file_paths: list[str],
        folder_id: str,
        progress_callback: Optional[
            Callable[[int, int, str], None]
        ] = None,
        conflict_solve_callback: Optional[
            Callable[[str], Awaitable[ConflictChoice]]
        ] = None,
        cancellation_event: threading.Event | None = None,
    ) -> list[dict]:
        if not self._gs.authenticated:
            raise UnauthenticatedError()

        results: list[dict] = []
        total = len(file_paths)
        for index, file_path in enumerate(file_paths):
            if cancellation_event and cancellation_event.is_set():
                for cancelled_path in file_paths[index:]:
                    results.append(self._result(
                        Path(cancelled_path).name,
                        success=False,
                        action="cancelled",
                        error_code="cancelled",
                        message="使用者取消上傳",
                    ))
                break

            result = await self._upload_single(
                file_path,
                folder_id,
                conflict_solve_callback,
            )
            results.append(result)
            if progress_callback:
                progress_callback(index + 1, total, Path(file_path).name)

        succeeded = sum(1 for result in results if result["success"])
        info(f"Drive 上傳完成：{succeeded}/{total}")
        return results

    async def _upload_single(
        self,
        file_path: str,
        folder_id: str,
        conflict_solve_callback: Optional[
            Callable[[str], Awaitable[ConflictChoice]]
        ],
    ) -> dict:
        path = Path(file_path)
        if not path.exists():
            return self._result(
                path.name,
                success=False,
                action="create",
                error_code="file_not_found",
                message=f"找不到檔案：{file_path}",
            )

        media = None
        try:
            existing_id = await self.find_file_id(path.name, folder_id)
            choice = ConflictChoice.NEW_VERSION
            if existing_id and conflict_solve_callback:
                choice = await conflict_solve_callback(path.name)

            if existing_id and choice is ConflictChoice.SKIP:
                return self._result(
                    path.name,
                    success=True,
                    file_id=existing_id,
                    action="skip",
                    message="沿用既有檔案",
                )

            media = MediaFileUpload(str(path), resumable=True)
            if existing_id and choice is ConflictChoice.OVERWRITE:
                action = "overwrite"

                def upload():
                    return self._upload_service.files().update(
                        fileId=existing_id,
                        media_body=media,
                        fields="id, name",
                        supportsAllDrives=True,
                    ).execute()
            else:
                action = "create"

                def upload():
                    return self._upload_service.files().create(
                        body={"name": path.name, "parents": [folder_id]},
                        media_body=media,
                        fields="id, name",
                        supportsAllDrives=True,
                    ).execute()

            response = await asyncio.to_thread(upload)
            return self._result(
                path.name,
                success=True,
                file_id=response.get("id", ""),
                action=action,
            )
        except Exception as exc:
            error(f"Drive {path.name} 上傳失敗：{exc}", exc_info=True)
            return self._result(
                path.name,
                success=False,
                file_id=existing_id if "existing_id" in locals() else "",
                action=action if "action" in locals() else "create",
                error_code="upload_failed",
                message=str(exc),
            )
        finally:
            file_handle = getattr(media, "_fd", None)
            if file_handle is not None and not file_handle.closed:
                file_handle.close()

    @staticmethod
    def _result(
        name: str,
        *,
        success: bool,
        file_id: str = "",
        action: str,
        error_code: str = "",
        message: str = "",
    ) -> dict:
        return {
            "name": name,
            "success": success,
            "file_id": file_id,
            "action": action,
            "error_code": error_code,
            "message": message,
        }
