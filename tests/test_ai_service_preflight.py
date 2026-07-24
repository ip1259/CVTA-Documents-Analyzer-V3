import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from ollama import ResponseError


from src.domain.orchestrator import DocumentProcessor
from src.infrastructure.ollama_client import OllamaClient


class OllamaClientAvailabilityTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = OllamaClient(model="qwen3.5:9b")
        self.client._client = SimpleNamespace(list=AsyncMock())

    async def test_service_and_model_are_available(self):
        self.client._client.list.return_value = {
            "models": [{"model": "qwen3.5:9b"}]
        }

        result = await self.client.check_availability()

        self.assertEqual((True, "", ""), result)

    async def test_supports_object_model_response(self):
        self.client._client.list.return_value = SimpleNamespace(
            models=[SimpleNamespace(model="qwen3.5:9b")]
        )

        result = await self.client.check_availability()

        self.assertTrue(result[0])

    async def test_model_not_found(self):
        self.client._client.list.return_value = {
            "models": [{"model": "another-model:latest"}]
        }

        available, error_code, message = (
            await self.client.check_availability()
        )

        self.assertFalse(available)
        self.assertEqual("MODEL_NOT_FOUND", error_code)
        self.assertIn("qwen3.5:9b", message)

    async def test_service_unreachable(self):
        self.client._client.list.side_effect = ConnectionError("offline")

        available, error_code, message = (
            await self.client.check_availability()
        )

        self.assertFalse(available)
        self.assertEqual("SERVICE_UNREACHABLE", error_code)
        self.assertIn("Ollama", message)

    async def test_service_api_error(self):
        self.client._client.list.side_effect = ResponseError(
            "bad response",
            status_code=500
        )

        available, error_code, message = (
            await self.client.check_availability()
        )

        self.assertFalse(available)
        self.assertEqual("SERVICE_ERROR", error_code)
        self.assertIn("API", message)

    async def test_service_timeout(self):
        async def never_returns():
            await asyncio.sleep(60)

        self.client._client.list.side_effect = never_returns

        with unittest.mock.patch(
            "src.infrastructure.ollama_client.HEALTH_TIMEOUT", 0.01
        ):
            available, error_code, message = (
                await self.client.check_availability()
            )

        self.assertFalse(available)
        self.assertEqual("SERVICE_TIMEOUT", error_code)
        self.assertIn("逾時", message)


class DocumentProcessorPreflightTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.processor = DocumentProcessor.__new__(DocumentProcessor)
        self.processor._storage = SimpleNamespace(
            _csv_file=Path("result.csv"),
            append_batch=Mock(return_value={
                "written": 0,
                "valid": 0,
                "invalid": 0,
                "skipped": 0,
                "errors": []
            }),
            save_for_copying=Mock()
        )

    async def test_failed_preflight_stops_batch_before_analysis(self):
        self.processor.check_ai_service = AsyncMock(return_value={
            "available": False,
            "error_code": "SERVICE_UNREACHABLE",
            "message": "offline",
            "model": "qwen3.5:9b"
        })
        self.processor.process_single = AsyncMock()

        result = await self.processor.process_batch(["first.jpg"])

        self.assertEqual(0, result["processed"])
        self.assertEqual(
            "SERVICE_UNREACHABLE",
            result["service_error"]["error_code"]
        )
        self.processor.check_ai_service.assert_awaited_once()
        self.processor.process_single.assert_not_awaited()
        self.processor._storage.append_batch.assert_not_called()

    async def test_successful_batch_runs_one_preflight(self):
        self.processor.check_ai_service = AsyncMock(return_value={
            "available": True,
            "error_code": "",
            "message": "",
            "model": "qwen3.5:9b"
        })
        self.processor.process_single = AsyncMock(return_value={
            "success": True,
            "image_path": "115001_first.jpg",
            "result": {},
            "error": ""
        })
        self.processor._storage.append_batch.return_value = {
            "written": 2,
            "valid": 2,
            "invalid": 0,
            "skipped": 0,
            "errors": []
        }

        result = await self.processor.process_batch([
            "115001_first.jpg",
            "115002_second.jpg"
        ])

        self.assertEqual(2, result["processed"])
        self.processor.check_ai_service.assert_awaited_once()
        self.assertEqual(2, self.processor.process_single.await_count)


class DocumentProcessorConfigurationTests(unittest.TestCase):
    def test_custom_prompts_path_is_supported(self):
        prompt_data = {"instruction": "test prompt"}
        with tempfile.TemporaryDirectory() as temp_dir:
            prompt_path = Path(temp_dir) / "prompts.json"
            prompt_path.write_text(
                json.dumps(prompt_data),
                encoding="utf-8"
            )
            with (
                patch("src.domain.orchestrator.OllamaClient"),
                patch("src.domain.orchestrator.LocalStorage"),
                patch("src.domain.orchestrator.OcrDataValidator")
            ):
                processor = DocumentProcessor(prompts_path=prompt_path)

        self.assertEqual(
            json.dumps(prompt_data, indent=2, ensure_ascii=False),
            processor._system_prompt
        )


if __name__ == "__main__":
    unittest.main()
