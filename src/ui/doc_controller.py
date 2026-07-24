from queue import Queue, Empty
import configparser
import threading
from PySide6.QtWidgets import QProgressDialog
import re
from pathlib import Path
from PySide6.QtCore import QObject, Property, Signal, Slot, Qt, QThread
from PySide6.QtWidgets import QFileDialog, QMessageBox
from typing import Optional, List, Any, Generator, Tuple

from src.infrastructure.document import Document
from src.infrastructure.google_workspace import GoogleServiceAccount, ConflictChoice
from src.infrastructure.data_storage import StorageBackend
from src.ui.table_model import DocumentTableModel
from src.infrastructure.logger import info, error
import asyncio
from src.domain.orchestrator import DocumentProcessor
from src.config import settings


class ProcessThread(QThread):
    errorOccurred = Signal(str)
    progressUpdated = Signal(int, str)
    finished = Signal(object)

    def __init__(self, action_generator: Generator[Tuple[int, str], Any, Any]):
        super().__init__()
        self.action_generator = action_generator
        self.stopFlag = False

    def run(self):
        """
        將原先 _safe_execute 的邏輯直接實作在這裡
        """
        try:
            while not self.stopFlag:
                try:
                    p, msg = next(self.action_generator)
                    self.progressUpdated.emit(p, msg)
                except StopIteration as final_result:
                    self.finished.emit(final_result.value)
                    return
            self.progressUpdated.emit(100, "操作已中斷")
            self.finished.emit(None)
        except Exception as e:
            error(f"發生未預期的錯誤: {str(e)}", exc_info=True)
            self.errorOccurred.emit(f"發生錯誤: {str(e)}")

    def stop(self):
        self.stopFlag = True


class DocController(QObject):
    selectedRowChanged = Signal()
    currentUnitChanged = Signal()
    currentDateChanged = Signal()
    currentOfficerChanged = Signal()
    currentCategoryChanged = Signal()
    currentNumberChanged = Signal()
    currentClassChanged = Signal()
    currentKeyPointChanged = Signal()
    currentImageSourceChanged = Signal()
    currentDocumentChanged = Signal()
    tableModelChanged = Signal()

    askConflictSignal = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._selectedRow = -1
        self._currentUnit = ""
        self._currentDate = ""
        self._currentOfficer = ""
        self._currentCategory = ""
        self._currentNumber = ""
        self._currentClass = ""
        self._currentKeyPoint = ""
        self._currentImageSource = ""
        self._currentDocument: Optional[Document] = None

        self._storage = StorageBackend()

        self._documents_list: List[Document] = self._storage.get_all_documents(
        )
        self._tableModel = DocumentTableModel(self._documents_list, self)

        self._service_account = GoogleServiceAccount()

        # 延後建立 AI client，避免設定檔缺失或內容錯誤時阻止 GUI 啟動。
        self._document_processor: Optional[DocumentProcessor] = None

        self._conflict_event = threading.Event()
        self._conflict_result = False
        self.askConflictSignal.connect(
            self.handleConflictResolution,
            Qt.ConnectionType.QueuedConnection
        )

        self._is_loading_document = False

    @Property(bool, constant=True)
    def shouldOpenSettings(self):
        """設定檔於本次啟動建立時，要求 GUI 顯示設定介面。"""
        return bool(settings.CONFIG_WAS_CREATED)

    @Property(int, notify=selectedRowChanged)
    def selectedRow(self):
        return self._selectedRow

    @selectedRow.setter
    def selectedRow(self, value):
        if self._selectedRow == value:
            return

        if self._tableModel and 0 <= value < self._tableModel.rowCount():
            self._selectedRow = value
            self.selectedRowChanged.emit()

            selected_doc = self._documents_list[value]

            self._update_current_document(selected_doc)
        else:
            self._selectedRow = -1
            self.selectedRowChanged.emit()
            self._update_current_document(None)

    def _update_current_document(self, doc: Optional[Document]):
        """內部方法：切換當前公文，並同步 UI 屬性，此時不應該觸發儲存"""
        self._currentDocument = doc
        self._is_loading_document = True

        if doc:
            self._currentUnit = doc.doc_from
            self._currentDate = doc.doc_date
            self._currentOfficer = doc.case_officer
            self._currentCategory = doc.doc_category
            self._currentNumber = doc.doc_number
            self._currentClass = doc.related_class
            self._currentKeyPoint = doc.key_points
            self._currentImageSource = doc.image_source
        else:
            self._currentUnit = ""
            self._currentDate = ""
            self._currentOfficer = ""
            self._currentCategory = ""
            self._currentNumber = ""
            self._currentClass = ""
            self._currentKeyPoint = ""
            self._currentImageSource = ""

        self.currentUnitChanged.emit()
        self.currentDateChanged.emit()
        self.currentOfficerChanged.emit()
        self.currentCategoryChanged.emit()
        self.currentNumberChanged.emit()
        self.currentClassChanged.emit()
        self.currentKeyPointChanged.emit()
        self.currentImageSourceChanged.emit()
        self.currentDocumentChanged.emit()

        self._is_loading_document = False

    @Property(str, notify=currentUnitChanged)
    def currentUnit(self):
        return self._currentUnit

    @currentUnit.setter
    def currentUnit(self, value):
        if self._currentUnit == value:
            return
        if not self._currentDocument:
            raise ValueError("[ERROR] 當前沒有選取公文")

        self._currentUnit = value
        self._currentDocument.doc_from = value
        self.currentUnitChanged.emit()

        if not self._is_loading_document:
            self.handleCurrentDocumentEdited()

    @Property(str, notify=currentDateChanged)
    def currentDate(self):
        return self._currentDate

    @currentDate.setter
    def currentDate(self, value):
        if self._currentDate == value:
            return
        if not self._currentDocument:
            raise ValueError("[ERROR] 當前沒有選取公文")

        self._currentDate = value
        self._currentDocument.doc_date = value
        self.currentDateChanged.emit()

        if not self._is_loading_document:
            self.handleCurrentDocumentEdited()

    @Property(str, notify=currentOfficerChanged)
    def currentOfficer(self):
        return self._currentOfficer

    @currentOfficer.setter
    def currentOfficer(self, value):
        if self._currentOfficer == value:
            return
        if not self._currentDocument:
            raise ValueError("[ERROR] 當前沒有選取公文")

        self._currentOfficer = value
        self._currentDocument.case_officer = value
        self.currentOfficerChanged.emit()

        if not self._is_loading_document:
            self.handleCurrentDocumentEdited()

    @Property(str, notify=currentCategoryChanged)
    def currentCategory(self):
        return self._currentCategory

    @currentCategory.setter
    def currentCategory(self, value):
        if self._currentCategory == value:
            return
        if not self._currentDocument:
            raise ValueError("[ERROR] 當前沒有選取公文")

        self._currentCategory = value
        self._currentDocument.doc_category = value
        self.currentCategoryChanged.emit()

        if not self._is_loading_document:
            self.handleCurrentDocumentEdited()

    @Property(str, notify=currentNumberChanged)
    def currentNumber(self):
        return self._currentNumber

    @currentNumber.setter
    def currentNumber(self, value):
        if self._currentNumber == value:
            return
        if not self._currentDocument:
            raise ValueError("[ERROR] 當前沒有選取公文")

        self._currentNumber = value
        self._currentDocument.doc_number = value
        self.currentNumberChanged.emit()

        if not self._is_loading_document:
            self.handleCurrentDocumentEdited()

    @Property(str, notify=currentClassChanged)
    def currentClass(self):
        return self._currentClass

    @currentClass.setter
    def currentClass(self, value):
        if self._currentClass == value:
            return
        if not self._currentDocument:
            raise ValueError("[ERROR] 當前沒有選取公文")

        self._currentClass = value
        self._currentDocument.related_class = value
        self.currentClassChanged.emit()

        if not self._is_loading_document:
            self.handleCurrentDocumentEdited()

    @Property(str, notify=currentKeyPointChanged)
    def currentKeyPoint(self):
        return self._currentKeyPoint

    @currentKeyPoint.setter
    def currentKeyPoint(self, value):
        if self._currentKeyPoint == value:
            return
        if not self._currentDocument:
            raise ValueError("[ERROR] 當前沒有選取公文")

        self._currentKeyPoint = value
        self._currentDocument.key_points = value
        self.currentKeyPointChanged.emit()

        if not self._is_loading_document:
            self.handleCurrentDocumentEdited()

    @Property(str, notify=currentImageSourceChanged)
    def currentImageSource(self):
        if self._currentImageSource:
            return Path(self._currentImageSource).as_uri()
        return ""

    @Property(Document, notify=currentDocumentChanged)
    def currentDocument(self):
        return self._currentDocument

    @currentDocument.setter
    def currentDocument(self, value):
        if self._currentDocument != value:
            self._currentDocument = value
            self.currentDocumentChanged.emit()

    @Property(QObject, constant=True)
    def tableModel(self):
        return self._tableModel

    @Slot()
    def addDocument(self):
        """
        開啟檔案選擇對話框，並在背景執行緒中處理檔案加入邏輯。
        """
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        file_dialog.setNameFilter("Images (*.png *.jpg *.jpeg)")

        if not file_dialog.exec_():
            return

        file_paths = file_dialog.selectedFiles()
        if not file_paths:
            return

        task_generator = self._add_documents_generator(file_paths)

        self._add_doc_thread = ProcessThread(task_generator)

        self._progress_dialog = QProgressDialog("正在準備處理檔案...", "取消", 0, 100)
        self._progress_dialog.setWindowTitle("匯入檔案進度")
        self._progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self._progress_dialog.setAutoClose(True)
        self._progress_dialog.setAutoReset(True)
        self._progress_dialog.setMinimumDuration(500)
        self._progress_dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        def onFinish(result):
            self._progress_dialog.close()

            if result is None:
                return

            success_count, error_messages = result

            self._documents_list.clear()
            self._documents_list.extend(self._storage.get_all_documents())
            self._tableModel.refresh_all()

            if error_messages:
                error_summary = f"成功匯入 {success_count} 筆檔案。\n部分檔案處理失敗（共 {len(error_messages)} 筆）："
                error_details = "\n".join(error_messages)

                msgBox = QMessageBox()
                msgBox.setIcon(QMessageBox.Icon.Warning)
                msgBox.setWindowTitle("部分匯入完成")
                msgBox.setText(error_summary)
                msgBox.setInformativeText(error_details)
                msgBox.exec()
            else:
                QMessageBox.information(
                    None,
                    "完成",
                    f"已成功匯入所有檔案 (共 {success_count} 筆)！"
                )

        def onError(error_msg):
            self._progress_dialog.close()
            QMessageBox.critical(
                None,
                "錯誤",
                f"背景任務發生嚴重錯誤：\n{error_msg}"
            )

        def onProgressUpdated(progress, status):
            self._progress_dialog.setValue(progress)
            self._progress_dialog.setLabelText(status)

        self._add_doc_thread.progressUpdated.connect(
            onProgressUpdated, Qt.ConnectionType.QueuedConnection)
        self._add_doc_thread.errorOccurred.connect(
            onError, Qt.ConnectionType.QueuedConnection)
        self._add_doc_thread.finished.connect(
            onFinish, Qt.ConnectionType.QueuedConnection)
        self._progress_dialog.canceled.connect(self._add_doc_thread.stop)

        self._progress_dialog.show()
        self._add_doc_thread.start()

    def _add_documents_generator(self, file_paths: List[str]) -> Generator[Tuple[int, str], Any, Tuple[int, List[str]]]:
        """
        背景執行的產生器核心邏輯。
        每次 yield 回傳 (百分比, 當前狀態訊息)。
        最終 return (成功數量, 錯誤訊息列表)。
        """
        success_count = 0
        error_messages = []
        total_files = len(file_paths)

        pattern = re.compile(r"^(\d{6})_.*\.(?:png|jpg|jpeg)$", re.IGNORECASE)

        for index, file_path in enumerate(file_paths):
            if hasattr(self, "_add_doc_thread") and self._add_doc_thread.stopFlag:
                error_messages.append("使用者手動中止後續檔案處理")
                break

            file_name = Path(file_path).name

            progress = int((index / total_files) * 100)
            yield progress, f"正在處理 ({index + 1}/{total_files}): {file_name}"

            if self._storage.get_document_by_id(file_path):
                error_messages.append(f"檔案 {file_name} 已存在於資料庫中，不重複加入")
                continue

            match = pattern.match(file_name)
            if not match:
                error_messages.append(f"檔名 {file_name} 不符合規則 (需為 6碼數字_檔名)，不加入")
                continue

            try:
                doc = Document()
                doc.image_source = file_path

                doc.serial_number = match.group(1)[3:6]

                self._storage.add_document(doc)
                success_count += 1
            except Exception as e:
                error_messages.append(f"處理 {file_name} 時發生異常: {str(e)}")

        yield 100, "處理完成"
        return success_count, error_messages

    @Slot()
    def analyzeDocument(self):
        """
        批次分析所有尚未分析的公文（仿照 addDocument 的 Threading & Progress 模式）。
        """
        try:
            if self._document_processor is None:
                self._document_processor = DocumentProcessor()
        except Exception as exc:
            error(f"AI 後端初始化失敗: {exc}", exc_info=True)
            QMessageBox.critical(
                None,
                "AI 設定錯誤",
                f"無法建立 AI 後端，請先修正設定：\n{exc}"
            )
            return

        all_docs = self._storage.get_all_documents()
        if not all_docs:
            QMessageBox.information(None, "提示", "目前資料庫中無任何公文可供分析。")
            return

        task_generator = self._analyze_documents_generator()

        self._analyze_doc_thread = ProcessThread(task_generator)

        progress_dialog = QProgressDialog("準備進行公文分析與驗證...", "取消", 0, 100)
        progress_dialog.setWindowTitle("公文批次分析進度")
        progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        progress_dialog.setAutoClose(True)
        progress_dialog.setAutoReset(True)
        progress_dialog.setMinimumDuration(500)

        progress_dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        def onFinish(result):
            progress_dialog.close()

            if result is None:
                return

            if result.get("cancelled"):
                QMessageBox.information(None, "已取消", "分析程序已中止。")
                return

            total = result.get("total", 0)
            success = result.get("success", 0)
            failed = result.get("failed", 0)

            self._documents_list.clear()
            self._documents_list.extend(self._storage.get_all_documents())
            self._tableModel.refresh_all()

            if self._selectedRow != -1:
                selected_doc = self._documents_list[self._selectedRow]
                self._update_current_document(selected_doc)

            summary_text = f"公文分析流程執行完畢！\n\n總共處理: {total} 筆\n成功筆數: {success} 筆\n失敗筆數: {failed} 筆"
            if failed > 0:
                QMessageBox.warning(None, "分析完成（含失敗）", summary_text)
            else:
                QMessageBox.information(None, "分析成功", summary_text)

        def onError(error_msg):
            progress_dialog.close()
            QMessageBox.critical(
                None,
                "錯誤",
                f"分析公文時發生嚴重錯誤：\n{error_msg}"
            )

        def onProgressUpdated(progress, status):
            progress_dialog.setValue(progress)
            progress_dialog.setLabelText(status)

        progress_dialog.canceled.connect(self._analyze_doc_thread.stop)
        self._analyze_doc_thread.finished.connect(onFinish)
        self._analyze_doc_thread.errorOccurred.connect(onError)
        self._analyze_doc_thread.progressUpdated.connect(onProgressUpdated)

        progress_dialog.show()
        self._analyze_doc_thread.start()

    def _analyze_documents_generator(self) -> Generator[Tuple[int, str], Any, dict]:
        """
        同步/非同步橋接產生器。
        負責在背景執行緒中運行 asyncio event loop，驅動 StorageBackend 的非同步分析流程。
        """
        # QThread 沒有事件迴圈；在工作執行緒建立專用 loop。
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async_gen = self._storage.analyze_all_documents_generator(
            self._document_processor)

        async def run_and_forward():
            """負責迭代非同步產生器，並將值傳回同步外層"""
            results = None
            try:
                async for progress_percent, status_msg in async_gen:
                    if self._analyze_doc_thread.stopFlag:
                        break

                    if progress_percent == "RESULT":
                        results = status_msg
                    else:
                        yield_queue.put_nowait((progress_percent, status_msg))
            except Exception as e:
                yield_queue.put_nowait(("ERROR", e))
            finally:
                yield_queue.put_nowait(("DONE", results))

        yield_queue = asyncio.Queue()

        task = loop.create_task(run_and_forward())

        while True:
            if hasattr(self, "_analyze_doc_thread") and self._analyze_doc_thread.stopFlag:
                task.cancel()
                loop.run_until_complete(
                    asyncio.gather(task, return_exceptions=True))
                yield 100, "操作已由使用者取消"
                return {"total": 0, "success": 0, "failed": 0, "cancelled": True}

            loop.run_until_complete(asyncio.sleep(0.05))

            while not yield_queue.empty():
                item = yield_queue.get_nowait()

                if item[0] == "ERROR":
                    loop.close()
                    raise item[1]

                if item[0] == "DONE":
                    loop.close()
                    return item[1]

                yield item[0], item[1]

    @Slot()
    def uploadDocument(self):
        """
        上傳公文圖檔至 Google Drive，並同步資料至 Google Sheets。
        """
        all_docs = self._storage.get_all_documents()
        if not all_docs:
            QMessageBox.information(None, "提示", "目前無任何公文資料可供上傳。")
            return

        self._upload_cancel_event = threading.Event()
        task_generator = self._upload_documents_generator()

        self._upload_doc_thread = ProcessThread(task_generator)

        self._upload_progress_dialog = QProgressDialog(
            "準備上傳至 Google 雲端硬碟...", "取消", 0, 100)
        self._upload_progress_dialog.setWindowTitle("雲端同步進度")
        self._upload_progress_dialog.setWindowModality(
            Qt.WindowModality.WindowModal)
        self._upload_progress_dialog.setAutoClose(True)
        self._upload_progress_dialog.setAutoReset(True)
        self._upload_progress_dialog.setMinimumDuration(500)
        self._upload_progress_dialog.setAttribute(
            Qt.WidgetAttribute.WA_DeleteOnClose)

        def onFinish(result):
            try:
                self._upload_progress_dialog.close()
            except RuntimeError:
                pass

            if result is None:
                return

            if result.get("cancelled"):
                QMessageBox.information(
                    None,
                    "已取消",
                    "已停止啟動新上傳；進行中的請求已安全結束。"
                )
                return

            if result.get("failed", 0) > 0:
                QMessageBox.warning(
                    None,
                    "上傳未完成",
                    f"Drive 上傳失敗 {result['failed']} 筆，"
                    "已取消 Google Sheets 同步。"
                )
                return

            self._documents_list.clear()
            self._documents_list.extend(self._storage.get_all_documents())
            self._tableModel.refresh_all()

            QMessageBox.information(None, "同步成功", "公文圖檔及資料已成功同步至 Google 雲端！")

        def onError(error_msg):
            try:
                self._upload_progress_dialog.close()
            except RuntimeError:
                pass
            QMessageBox.critical(
                None,
                "錯誤",
                f"上傳或同步時發生錯誤：\n{error_msg}"
            )

        def onProgressUpdated(progress, status):
            try:
                self._upload_progress_dialog.setValue(progress)
                self._upload_progress_dialog.setLabelText(status)
            except RuntimeError:
                pass

        self._upload_progress_dialog.canceled.connect(
            self._upload_cancel_event.set)

        self._upload_doc_thread.finished.connect(
            onFinish, Qt.ConnectionType.QueuedConnection)

        self._upload_doc_thread.errorOccurred.connect(
            onError, Qt.ConnectionType.QueuedConnection)

        self._upload_doc_thread.progressUpdated.connect(
            onProgressUpdated, Qt.ConnectionType.QueuedConnection)

        self._upload_progress_dialog.show()
        self._upload_doc_thread.start()

    def _upload_documents_generator(self) -> Generator[Tuple[int, str], Any, dict]:
        """
        處理 Google Drive 上傳與 Google Sheets 同步的背景產生器橋接。
        """
        q = Queue()

        def progress_cb(progress_percent, filename):
            q.put(("PROGRESS", progress_percent, f"正在上傳: {filename}"))

        def conflict_cb(filename):
            return ConflictChoice.SKIP

        def worker_thread():
            try:
                upload_summary = self._storage.upload_to_google_drive(
                    google_account_service=self._service_account,
                    progress_callback=progress_cb,
                    conflict_callback=conflict_cb,
                    cancellation_event=self._upload_cancel_event
                )

                if upload_summary["success"]:
                    q.put(("PROGRESS", 95, "圖檔處理完畢，正在同步資料至 Google Sheets..."))
                    self._storage.sync_to_google_sheets(
                        self._service_account
                    )
                    upload_summary["sheets_synced"] = True
                else:
                    upload_summary["sheets_synced"] = False

                q.put(("DONE", upload_summary))
            except Exception as e:
                q.put(("ERROR", e))

        t = threading.Thread(target=worker_thread)
        t.daemon = True
        t.start()

        while True:
            if hasattr(self, "_upload_doc_thread") and self._upload_doc_thread.stopFlag:
                return {"cancelled": True}

            try:
                item = q.get(timeout=0.1)

                if item[0] == "PROGRESS":
                    yield item[1], item[2]
                elif item[0] == "DONE":
                    yield 100, "同步完成！"
                    return item[1]
                elif item[0] == "ERROR":
                    raise Exception(str(item[1]))

            except Empty:
                continue

    @Slot(str)
    def handleConflictResolution(self, filename: str):
        """
        在主執行緒中跳出對話框，接收到使用者回應後解鎖背景執行緒。
        """
        reply = QMessageBox.question(
            None,
            "檔案衝突",
            f"雲端硬碟中已存在同名檔案：{filename}\n是否要覆寫檔案？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        self._conflict_result = (reply == QMessageBox.StandardButton.Yes)

        self._conflict_event.set()

    @Slot()
    def openArchive(self):
        """開啟歸檔（讀取本地 JSON）"""
        try:
            self._storage.load_from_json()
            self._documents_list.clear()
            self._documents_list.extend(self._storage.get_all_documents())
            self._tableModel.refresh_all()
            info("歸檔資料已成功載入")
        except Exception as e:
            error(f"開啟歸檔失敗: {e}")
            QMessageBox.critical(
                None,
                "開啟歸檔失敗",
                f"開啟歸檔失敗: {e}"
            )

    @Slot()
    def saveArchive(self):
        """儲存歸檔（持久化至本地 JSON）"""
        try:
            self._storage.save_to_json()
            info("歸檔資料已成功保存")
        except Exception as e:
            error(f"儲存歸檔失敗: {e}")
            QMessageBox.critical(
                None,
                "儲存歸檔失敗",
                f"儲存歸檔失敗: {e}"
            )

    @Slot()
    def clearAllData(self):
        """清除所有資料"""
        self._storage.clear()
        self._documents_list.clear()
        self._tableModel.refresh_all()
        self._update_current_document(None)
        info("所有資料已清除")

    @Slot()
    def openSettings(self):
        print("開啟設定")

    @Slot(result="QVariantMap")
    def getSettings(self):
        return {
            "ollamaHost": str(settings.OLLAMA_HOST),
            "ollamaModel": str(settings.OLLAMA_MODEL),
            "healthTimeout": int(settings.OLLAMA_HEALTH_TIMEOUT),
            "requestTimeout": int(settings.OLLAMA_REQUEST_TIMEOUT),
            "promptsPath": str(settings.PROMPTS_PATH),
            "spreadsheetId": str(settings.GOOGLE_SPREADSHEET_ID or ""),
            "sheetName": str(settings.SHEET_NAME or ""),
            "targetFolderName": str(settings.TARGET_FOLDER_NAME or ""),
        }

    @Slot(result=str)
    def selectPromptsFile(self):
        file_path, _ = QFileDialog.getOpenFileName(
            None,
            "選擇提示詞設定檔",
            str(settings.CONFIG_DIR),
            "JSON 檔案 (*.json)"
        )
        return file_path

    @Slot("QVariantMap", result="QVariantMap")
    def saveSettings(self, values):
        host = str(values.get("ollamaHost", "")).strip().rstrip("/")
        model = str(values.get("ollamaModel", "")).strip()
        prompts_path = Path(
            str(values.get("promptsPath", "")).strip()
        ).expanduser()

        if not host.startswith(("http://", "https://")):
            return {
                "success": False,
                "message": "Ollama 位址必須以 http:// 或 https:// 開頭。"
            }
        if not model:
            return {"success": False, "message": "請輸入 Ollama 模型名稱。"}
        if not prompts_path.is_file() or prompts_path.suffix.lower() != ".json":
            return {
                "success": False,
                "message": "提示詞設定檔必須是存在的 JSON 檔案。"
            }

        try:
            health_timeout = int(values.get("healthTimeout", 5))
            request_timeout = int(values.get("requestTimeout", 300))
        except (TypeError, ValueError):
            return {"success": False, "message": "逾時秒數必須是整數。"}

        if health_timeout < 1 or request_timeout < 1:
            return {"success": False, "message": "逾時秒數必須大於 0。"}

        config_path = settings.CONFIG_DIR / "settings.cfg"
        parser = configparser.ConfigParser(interpolation=None)
        parser.read(config_path, encoding="utf-8")
        for section in ("Ollama", "Google"):
            if not parser.has_section(section):
                parser.add_section(section)

        parser["Ollama"].update({
            "OLLAMA_HOST": host,
            "OLLAMA_MODEL": model,
            "OLLAMA_HEALTH_TIMEOUT": str(health_timeout),
            "OLLAMA_REQUEST_TIMEOUT": str(request_timeout),
            "PROMPTS_PATH": str(prompts_path.resolve()),
        })
        parser["Google"].update({
            "GOOGLE_SPREADSHEET_ID": str(
                values.get("spreadsheetId", "")
            ).strip(),
            "SHEET_NAME": str(values.get("sheetName", "")).strip(),
            "TARGET_FOLDER_NAME": str(
                values.get("targetFolderName", "")
            ).strip(),
        })

        try:
            with config_path.open("w", encoding="utf-8") as config_file:
                parser.write(config_file)

            settings.OLLAMA_HOST = host
            settings.OLLAMA_MODEL = model
            settings.OLLAMA_HEALTH_TIMEOUT = health_timeout
            settings.OLLAMA_REQUEST_TIMEOUT = request_timeout
            settings.PROMPTS_PATH = prompts_path.resolve()
            settings.GOOGLE_SPREADSHEET_ID = parser["Google"][
                "GOOGLE_SPREADSHEET_ID"
            ]
            settings.SHEET_NAME = parser["Google"]["SHEET_NAME"]
            settings.TARGET_FOLDER_NAME = parser["Google"][
                "TARGET_FOLDER_NAME"
            ]
            # 下次分析時才依新設定建立 client；設定視窗不應因後端錯誤關閉失敗。
            self._document_processor = None
            info("設定已更新")
            return {"success": True, "message": "設定已儲存並立即套用。"}
        except Exception as exc:
            error(f"儲存設定失敗: {exc}", exc_info=True)
            return {"success": False, "message": f"儲存設定失敗：{exc}"}

    @Slot(int)
    def handleRowChanged(self, row):
        self.selectedRow = row

    def handleCurrentDocumentEdited(self):
        """當使用者透過側邊表單修改欄位時觸發此處"""
        if self._currentDocument:
            self._storage.update_document(
                self._currentImageSource, self._currentDocument)

            if 0 <= self._selectedRow < self._tableModel.rowCount():
                top_left = self._tableModel.index(self._selectedRow, 0)
                bottom_right = self._tableModel.index(
                    self._selectedRow, self._tableModel.columnCount() - 1)
                self._tableModel.dataChanged.emit(
                    top_left, bottom_right, [Qt.ItemDataRole.DisplayRole])
