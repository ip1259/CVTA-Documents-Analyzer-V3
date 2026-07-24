import logging
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from src.infrastructure import logger as logger_module
from src.infrastructure.data_storage import StorageBackend
from src.infrastructure.document import Document
from src.infrastructure.google_workspace import (
    ConflictChoice,
    GoogleServiceAccount,
    UnauthenticatedError,
)
from src.infrastructure.google_workspace.drive_service import (
    GoogleDriveService,
)
from src.ui.doc_controller import DocController


class StorageLifecycleTests(unittest.TestCase):
    def test_storage_instances_are_independent(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            first = StorageBackend(
                str(Path(temp_dir) / "first.json")
            )
            second = StorageBackend(
                str(Path(temp_dir) / "second.json")
            )
            first.add_document(Document(
                serial_number="001",
                image_source="115001_first.jpg",
            ))

            self.assertEqual(1, len(first.get_all_documents()))
            self.assertEqual([], second.get_all_documents())


class LoggingLifecycleTests(unittest.TestCase):
    def test_initialization_is_idempotent_and_preserves_root_handlers(self):
        root = logging.getLogger()
        sentinel = logging.NullHandler()
        root.addHandler(sentinel)
        try:
            logger_module.app_logger.handlers.clear()
            logger_module.app_logger.addHandler(logging.NullHandler())
            logger_module.app_logger._cvta_initialized = False
            with tempfile.TemporaryDirectory() as temp_dir:
                first = logger_module.initialize_logging(temp_dir)
                handler_count = len(first.handlers)
                second = logger_module.initialize_logging(temp_dir)

                self.assertIs(first, second)
                self.assertEqual(handler_count, len(second.handlers))
                self.assertIn(sentinel, root.handlers)
                for handler in logger_module.app_logger.handlers:
                    handler.close()
                logger_module.app_logger.handlers.clear()
                logger_module.app_logger.addHandler(logging.NullHandler())
                logger_module.app_logger._cvta_initialized = False
        finally:
            root.removeHandler(sentinel)
            for handler in logger_module.app_logger.handlers:
                handler.close()
            logger_module.app_logger.handlers.clear()
            logger_module.app_logger.addHandler(logging.NullHandler())
            logger_module.app_logger._cvta_initialized = False


class GoogleAuthenticationTests(unittest.TestCase):
    def test_failed_authentication_leaves_safe_state(self):
        account = GoogleServiceAccount(
            service_account_path="missing-service-account.json",
            client_secret_path="missing-client-secret.json",
            token_path="missing-token.json",
        )

        self.assertFalse(account.authenticated)
        self.assertEqual("", account.service_account_email)
        with self.assertRaises(UnauthenticatedError):
            _ = account.drive_service


class GoogleDriveServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_cancellation_stops_starting_new_uploads(self):
        account = SimpleNamespace(authenticated=True)
        service = GoogleDriveService(account)
        service._upload_single = AsyncMock(return_value={
            "name": "first.jpg",
            "success": True,
            "file_id": "id-1",
            "action": "create",
            "error_code": "",
            "message": "",
        })
        cancellation_event = threading.Event()

        def progress(*_):
            cancellation_event.set()

        results = await service.upload_files(
            ["first.jpg", "second.jpg", "third.jpg"],
            "folder",
            progress_callback=progress,
            cancellation_event=cancellation_event,
        )

        self.assertEqual(1, service._upload_single.await_count)
        self.assertTrue(results[0]["success"])
        self.assertEqual("cancelled", results[1]["action"])
        self.assertEqual("cancelled", results[2]["action"])

    async def test_overwrite_failure_is_not_reported_as_success(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "document.jpg"
            image_path.write_bytes(b"image")

            upload_request = Mock()
            upload_request.execute.side_effect = RuntimeError("update failed")
            files_api = Mock()
            files_api.update.return_value = upload_request
            upload_service = Mock()
            upload_service.files.return_value = files_api
            account = SimpleNamespace(
                authenticated=True,
                upload_drive_service=upload_service,
            )
            service = GoogleDriveService(account)
            service.find_file_id = AsyncMock(return_value="existing-id")

            async def overwrite(_):
                return ConflictChoice.OVERWRITE

            result = await service._upload_single(
                str(image_path),
                "folder",
                overwrite,
            )

        self.assertFalse(result["success"])
        self.assertEqual("overwrite", result["action"])
        self.assertEqual("existing-id", result["file_id"])


class CloudSyncFlowTests(unittest.TestCase):
    def test_sheets_sync_is_skipped_after_drive_failure(self):
        controller = DocController.__new__(DocController)
        controller._storage = Mock()
        controller._storage.upload_to_google_drive.return_value = {
            "success": False,
            "cancelled": False,
            "uploaded": 1,
            "failed": 1,
            "results": [],
        }
        controller._service_account = object()
        controller._upload_cancel_event = threading.Event()
        controller._upload_doc_thread = SimpleNamespace(stopFlag=False)

        list(controller._upload_documents_generator())

        controller._storage.sync_to_google_sheets.assert_not_called()


if __name__ == "__main__":
    unittest.main()
