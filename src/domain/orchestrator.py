import sys
import os
import asyncio
from pathlib import Path
from src.infrastructure.logger import (
    catch_exception,
    error,
    info,
    initialize_logging,
    warning,
)
from src.infrastructure.ollama_client import OllamaClient
from src.infrastructure.local_storage import LocalStorage
from src.domain.validator import OcrDataValidator
from src.config import settings
import json


class DocumentProcessor:
    """公文處理協調器 - 整合完整流程"""

    def __init__(self, prompts_path: str | Path | None = None):
        self._prompts_path = Path(prompts_path or settings.PROMPTS_PATH)
        self._system_prompt = self._load_system_prompt()
        self._ollama = OllamaClient(
            model=settings.OLLAMA_MODEL,
            system_prompt=self._system_prompt
        )
        self._validator = OcrDataValidator()
        self._storage = LocalStorage()

    def _load_system_prompt(self) -> str:
        """載入 prompts.json 設定"""
        try:
            with self._prompts_path.open('r', encoding='utf-8') as f:
                sys_prompt = json.load(f)
                sys_prompt = json.dumps(sys_prompt,
                                        indent=2, ensure_ascii=False)
                return sys_prompt
        except Exception as e:
            error(f"載入 prompts.json 失敗：{e}")
            warning("將使用預設參數")
            return ""

    async def check_ai_service(self) -> dict:
        """Check AI service availability before document analysis."""
        available, error_code, message = (
            await self._ollama.check_availability()
        )
        return {
            "available": available,
            "error_code": error_code,
            "message": message,
            "model": self._ollama.model
        }

    @catch_exception
    async def process_single(self, image_path: str) -> dict:
        """
        處理單張公文圖片

        Args:
            image_path: 圖片路徑

        Returns:
            完整處理結果 dict
        """
        info(f"開始處理圖片：{image_path}")

        try:
            raw_data = await self._ollama.generate(image_path)

            if isinstance(raw_data, list):
                parsed_data = json.loads(raw_data[0]) if raw_data else {}
            else:
                parsed_data = json.loads(raw_data) if raw_data else {}

            info("執行資料驗證...")
            is_valid, error_code, result = self._validator.validate_and_prepare(
                parsed_data)

            return {
                "success": is_valid,
                "image_path": image_path,
                "raw_data": parsed_data,
                "result": result.get("csv_data", {}),
                "error": error_code
            }

        except Exception as e:
            error(f"處理失敗 {image_path}: {e}", exc_info=True)
            return {
                "success": False,
                "image_path": image_path,
                "error": str(e)
            }

    async def process_batch(self, image_paths: list, extra_output: bool = False) -> dict:
        """批次處理多張圖片"""
        info(f"批次處理 {len(image_paths)} 張圖片")

        service_status = await self.check_ai_service()
        if not service_status["available"]:
            warning(
                f"AI service preflight failed: "
                f"{service_status['error_code']} - "
                f"{service_status['message']}"
            )
            return {
                "processed": 0,
                "success": 0,
                "failed": 0,
                "csv_file": str(self._storage._csv_file),
                "results": [],
                "service_error": service_status
            }

        results = await asyncio.gather(*[
            self.process_single(img) for img in image_paths
        ])

        prepared_data = []
        for r in results:
            filename = os.path.basename(r["image_path"])
            base_name = filename.split('_')[0]
            serial_number = base_name[3:6] if len(base_name) >= 6 else ""

            csv_data = r.get("result", {}).copy()
            csv_data["serial_number"] = serial_number

            prepared_data.append({
                **r,
                "is_valid": r["success"],
                "csv_data": csv_data,
                "error_code": r.get("error", ""),
                "serial_number": serial_number
            })

        storage_stats = self._storage.append_batch(prepared_data)

        if extra_output:
            self._storage.save_for_copying(prepared_data)

        info(
            f"批次處理完成：寫入 {storage_stats['written']}/"
            f"{len(image_paths)}，跳過 {storage_stats['skipped']}"
        )

        return {
            "processed": len(results),
            "success": sum(1 for r in results if r.get("success")),
            "failed": sum(1 for r in results if not r.get("success")),
            "csv_file": str(self._storage._csv_file),
            "results": prepared_data,
            "storage": storage_stats
        }


@catch_exception
async def main():
    """CLI 測試程式碼"""
    import argparse

    initialize_logging()

    parser = argparse.ArgumentParser(description="CVTA 公文 OCR 分析器")
    parser.add_argument("--images", nargs="*", type=str, required=True,
                        help="圖片路徑列表")
    parser.add_argument("--extra_output", action="store_true",
                        help="額外產出用於複製的 CSV 檔案")
    args = parser.parse_args()

    if not args.images:
        print("請提供圖片路徑或建立 .env 檔案")
        sys.exit(1)

    processor = DocumentProcessor()

    result = await processor.process_batch(args.images, args.extra_output)

    if result.get("service_error"):
        service_error = result["service_error"]
        print(
            f"AI 服務確認失敗 [{service_error['error_code']}]："
            f"{service_error['message']}"
        )
        raise SystemExit(1)

    print("\n=== 處理結果 ===")
    print(f"處理圖片：{result['processed']} 張")
    print(f"成功：{result['success']} 筆")
    print(f"失敗：{result['failed']} 筆")
    print(f"CSV 檔案：{result['csv_file']}")


if __name__ == "__main__":
    asyncio.run(main())
