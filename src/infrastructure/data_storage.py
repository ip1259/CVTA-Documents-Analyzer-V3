"""資料儲存後端容器 - 搭配 tableModel、sheet_service、doc_controller 使用。

本模組提供一個型別安全的儲存後端，支援：
- 基本 CRUD 操作（以 Document 物件為核心）
- 本地 JSON 持久化
- 同步至 Google Sheets
"""

from typing import Callable
import json
import threading
import asyncio
from pathlib import Path
from typing import Dict, List, Optional
import re

from src.infrastructure.logger import info, warning, error
from src.infrastructure.document import Document
from src.infrastructure.google_workspace.sheets_service import GoogleSheetsService
from src.infrastructure.google_workspace.drive_service import GoogleDriveService
from src.infrastructure.google_workspace import GoogleServiceAccount, ConflictChoice
from src.domain.orchestrator import DocumentProcessor

from src.config.settings import TARGET_FOLDER_NAME


class StorageError(Exception):
    """儲存後端錯誤類別。"""
    pass


class StorageBackend:
    """資料儲存後端容器（單例執行緒安全版）。

    內部使用 dict[str, Document] 儲存，以提供 O(1) 的查詢與更新效能。
    採用單例模式（Singleton），確保全域僅有一個資料源。
    """

    def __new__(cls, *args, **kwargs):
        """確保全域只有一個 StorageBackend 實例（執行緒安全）。"""
        return super().__new__(cls)

    def __init__(self, json_path: str = "data/output_results/documents.json"):
        """初始化單例儲存後端。"""
        self._json_path = Path(json_path)

        self._json_path.parent.mkdir(parents=True, exist_ok=True)

        self._lock = threading.RLock()

        self._data: Dict[str, Document] = {}


    def _get_storage(self, dict_mode: bool = False) -> Dict[str, Document | dict]:
        """獲取當前資料字典（已移除 thread_local 邏輯）。"""
        if dict_mode:
            return {k: v.to_dict() for k, v in self._data.items()}
        return self._data

    def add_document(self, doc: Document) -> None:
        """新增公文。"""
        if not doc.image_source:
            raise StorageError("公文圖片來源（image_source）不能為空")
        else:
            file_name = Path(doc.image_source).name
            pattern = re.compile(r"^(\d{6})_(.*)$")
            match = pattern.match(file_name)
            if not match:
                raise StorageError(
                    "檔名格式錯誤，檔名應以6碼數字開頭, 格式為'民國年(3碼)+流水號(3碼)_...'")

        with self._lock:
            storage = self._get_storage()
            if doc.image_source in storage:
                raise StorageError(f"圖片來源 {doc.image_source} 已存在")

            doc.serial_number = file_name[3:6]
            storage[doc.image_source] = doc
            info(f"成功新增公文：{doc.image_source}")

    def update_document(self, img_src: str, updated_doc: Document) -> None:
        """更新公文。

        Args:
            img_src: 要更新的公文的圖片來源，作為唯一識別項
            updated_doc: 包含新資料的 Document 物件
        """
        with self._lock:
            storage = self._get_storage()
            if img_src not in storage:
                raise StorageError(f"找不到要更新的公文：{img_src}")

            if updated_doc.image_source and updated_doc.image_source != img_src:
                raise StorageError("不可變更公文的圖片來源（image_source）")

            storage[img_src] = updated_doc
            info(f"成功更新公文：{img_src}")

    def delete_document(self, img_src: str) -> None:
        """刪除公文。"""
        with self._lock:
            storage = self._get_storage()
            if img_src not in storage:
                raise StorageError(f"找不到要刪除的公文：{img_src}")

            del storage[img_src]
            info(f"成功刪除公文：{img_src}")

    def get_document_by_id(self, img_src: str) -> Optional[Document]:
        """依圖片來源取得公文物件。"""
        with self._lock:
            return self._get_storage().get(img_src)

    def get_all_documents(self) -> List[Document]:
        """取得所有公文物件列表。"""
        with self._lock:
            unordered = list(self._get_storage().values())
            ordered = sorted(unordered, key=lambda x: x.serial_number)
            return ordered

    def clear(self) -> None:
        """清空記憶體中的所有資料。"""
        with self._lock:
            self._get_storage().clear()
            info("已清空記憶體中的公文資料")

    def save_to_json(self) -> None:
        """將當前資料持久化儲存至 JSON。"""
        with self._lock:
            try:
                storage = self._get_storage(dict_mode=True)
                with open(self._json_path, "w", encoding="utf-8") as f:
                    json.dump(storage, f)
                info(f"資料成功持久化至 JSON：{self._json_path}")
            except Exception as e:
                error(f"JSON 持久化失敗：{e}", exc_info=True)
                raise StorageError(f"JSON 持久化失敗: {e}")

    def load_from_json(self) -> int:
        """自 JSON 檔案載入資料。"""
        if not self._json_path.exists():
            return 0
        try:
            with self._lock:
                storage = self._get_storage()
                with open(self._json_path, "r", encoding="utf-8") as f:
                    data_list = json.load(f)
                    for key, item in data_list.items():
                        doc = Document(
                            serial_number=item.get("流水號") or item.get(
                                "serial_number") or "",
                            doc_date=item.get("日期") or item.get(
                                "doc_date") or "",
                            related_class=item.get("班級") or item.get(
                                "related_class") or "",
                            doc_from=item.get("發文機關") or item.get(
                                "doc_from") or "",
                            doc_category=item.get("字別") or item.get(
                                "doc_category") or "",
                            doc_number=item.get("文號") or item.get(
                                "doc_number") or "",
                            key_points=item.get("事由") or item.get(
                                "key_points") or "",
                            case_officer=item.get("承辦人") or item.get(
                                "case_officer") or "",
                            image_source=item.get("image_source") or item.get(
                                "影像來源路徑") or "",
                            analyzed=item.get("analyzed", False),
                            drive_file_id=item.get("drive_file_id") or ""
                        )
                        if doc.image_source:
                            storage[doc.image_source] = doc
            return len(storage)
        except Exception as e:
            error(f"JSON 載入失敗：{e}", exc_info=True)
            raise StorageError(str(e))

    async def analyze_all_documents_generator(self, processor: DocumentProcessor):
        """
        批次分析並驗證所有公文的非同步產生器。

        Args:
            processor: DocumentProcessor 實例，負責 OCR 提取與 OcrDataValidator 驗證。

        Yields:
            tuple[int, str]: (進度百分比, 當前步驟描述)

        Returns:
            dict: 包含 success_count, failed_count 與 total_count 的處理結果字典
        """
        with self._lock:
            all_docs = self.get_all_documents()

        total_docs = len(all_docs)
        if total_docs == 0:
            info("無任何公文需要進行分析。")
            yield 100, "無任何公文需要進行分析"
            yield "RESULT", {"total": 0, "success": 0, "failed": 0}
            return

        success_count = 0
        failed_count = 0

        yield 0, "正在確認 AI 服務可用性..."
        service_status = await processor.check_ai_service()
        if not service_status["available"]:
            raise RuntimeError(
                f"AI 服務確認失敗 [{service_status['error_code']}]："
                f"{service_status['message']}"
            )

        info(f"開始批次分析流程，共 {total_docs} 筆公文。")

        for idx, doc in enumerate(all_docs, start=1):
            progress_percent = int(((idx - 1) / total_docs) * 100)

            file_name = Path(
                doc.image_source).name if doc.image_source else "未知檔案"
            yield progress_percent, f"正在分析第 {idx}/{total_docs} 筆：{file_name}..."

            try:
                process_result = await processor.process_single(doc.image_source)

                with self._lock:
                    if process_result.get("success"):
                        csv_data = process_result.get("result", {})

                        doc.doc_date = csv_data.get("doc_date", doc.doc_date)
                        doc.related_class = csv_data.get(
                            "related_class", doc.related_class)
                        doc.doc_from = csv_data.get("doc_from", doc.doc_from)
                        doc.doc_category = csv_data.get(
                            "doc_category", doc.doc_category)
                        doc.doc_number = csv_data.get(
                            "doc_number", doc.doc_number)
                        doc.key_points = csv_data.get(
                            "key_points", doc.key_points)
                        doc.case_officer = csv_data.get(
                            "case_officer", doc.case_officer)
                        doc.analyzed = True

                        success_count += 1
                        info(f"公文 [{file_name}] 分析暨驗證成功。")
                    else:
                        doc.analyzed = False
                        failed_count += 1
                        error_msg = process_result.get("error", "未知錯誤")
                        warning(f"公文 [{file_name}] 分析驗證失敗：{error_msg}")

            except Exception as e:
                failed_count += 1
                error(f"分析公文 [{file_name}] 時發生非預期異常：{e}", exc_info=True)

        try:
            yield 95, "正在將分析結果持久化至本地 JSON..."
            self.save_to_json()
        except Exception as e:
            error(f"分析後自動存檔失敗：{e}")

        yield 100, f"分析完成！成功: {success_count} 筆, 失敗: {failed_count} 筆"

        yield "RESULT", {
            "total": total_docs,
            "success": success_count,
            "failed": failed_count
        }

    def upload_to_google_drive(self, google_account_service: GoogleServiceAccount,
                               progress_callback: Optional[Callable[[
                                   int, str], None]] = None,
                               conflict_callback: Optional[Callable[[str], ConflictChoice]] = None,
                               cancellation_event: threading.Event | None = None) -> dict:
        """將所有公文上傳至 Google Drive（支援圖片），並更新公文的雲端檔案 ID。"""

        try:
            with self._lock:
                docs_to_upload = []
                upload_target_imgs = []
                missing_images = []
                for doc in self.get_all_documents():
                    if doc.drive_file_id:
                        continue
                    if doc.image_source and Path(doc.image_source).exists():
                        docs_to_upload.append(doc)
                        upload_target_imgs.append(doc.image_source)
                    else:
                        missing_images.append(doc.image_source)

            if missing_images:
                return {
                    "success": False,
                    "cancelled": False,
                    "uploaded": 0,
                    "failed": len(missing_images),
                    "results": [
                        {
                            "name": Path(path).name if path else "",
                            "success": False,
                            "file_id": "",
                            "action": "create",
                            "error_code": "file_not_found",
                            "message": f"找不到圖片：{path}",
                        }
                        for path in missing_images
                    ],
                }

            if not upload_target_imgs:
                info("沒有需要上傳的公文圖片")
                return {
                    "success": True,
                    "cancelled": False,
                    "uploaded": 0,
                    "failed": 0,
                    "results": []
                }

            async def _async_upload_flow():
                drive_service = GoogleDriveService(google_account_service)
                if not TARGET_FOLDER_NAME:
                    raise StorageError("未設定 Google Drive 目標資料夾")
                folder_id = await drive_service.find_folder_id(TARGET_FOLDER_NAME)
                if not folder_id:
                    raise StorageError(
                        f"找不到 Google Drive 目標資料夾：{TARGET_FOLDER_NAME}")

                def inner_progress(completed_count, total_count, filename):
                    if progress_callback:
                        progress_callback(
                            int(completed_count / total_count * 100), filename)

                async def inner_conflict(filename):
                    if conflict_callback:
                        return conflict_callback(filename)
                    return ConflictChoice.SKIP

                return await drive_service.upload_files(
                    file_paths=upload_target_imgs,
                    folder_id=folder_id,
                    progress_callback=inner_progress,
                    conflict_solve_callback=inner_conflict,
                    cancellation_event=cancellation_event
                )

            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            upload_results = loop.run_until_complete(_async_upload_flow())

            with self._lock:
                id_map = {
                    result["name"]: result["file_id"]
                    for result in upload_results
                    if result["success"] and result["file_id"]
                }

                updated_count = 0
                for doc in docs_to_upload:
                    fname = Path(doc.image_source).name
                    if fname in id_map:
                        doc.drive_file_id = id_map[fname]
                        updated_count += 1

            info(f"Google Drive 上傳完成，成功同步更新 {updated_count} 筆公文的雲端 ID")

        except Exception as e:
            error(f"Google Drive 上傳失敗：{e}", exc_info=True)
            raise StorageError(str(e))

        self.save_to_json()
        failed_count = sum(
            1 for result in upload_results
            if not result["success"] and result["action"] != "cancelled"
        )
        cancelled = any(
            result["action"] == "cancelled" for result in upload_results
        )
        return {
            "success": failed_count == 0 and not cancelled,
            "cancelled": cancelled,
            "uploaded": sum(
                1 for result in upload_results if result["success"]
            ),
            "failed": failed_count,
            "results": upload_results,
        }

    def sync_to_google_sheets(self, google_account_service: GoogleServiceAccount) -> None:
        """將資料同步至 Google Sheets。"""
        try:
            sheets_service = GoogleSheetsService(google_account_service)
            with self._lock:
                rows = {}
                for doc in self.get_all_documents():
                    sheet_name = Path(doc.image_source).name[:3] + "年度"
                    if sheet_name not in rows:
                        rows[sheet_name] = []
                    row = sheets_service.format_sheet_row_with_id(
                        doc.to_dict(), doc.drive_file_id)
                    rows[sheet_name].append(row)

            if not rows:
                info("無資料可同步至 Google Sheets")
                return

            for sheet_name, row_data in rows.items():
                template_sheet_id = sheets_service.get_sheet_id_by_name("範本")
                if template_sheet_id is None:
                    raise StorageError("找不到 '範本' 工作表")
                sheet_id = sheets_service.get_sheet_id_by_name(sheet_name)
                if sheet_id is None:
                    sheets_service.duplicate_sheet("範本", sheet_name)
                sheet_range = f"{sheet_name}!A1"
                sheets_service.append_values(row_data, sheet_range)
            info(f"已同步 {len(rows)} 筆資料至 Google Sheets")
        except Exception as e:
            error(f"同步至 Google Sheets 失敗：{e}", exc_info=True)
            raise StorageError(str(e))

    def _get_data_list_for_persistance(self) -> List[Document]:
        """內部輔助方法：獲取用於持久化的資料列表。"""
        return self.get_all_documents()
