import sys
import os
import asyncio
from src.infrastructure.logger import info, warning, error, catch_exception
from src.infrastructure.ollama_client import OllamaClient
from src.infrastructure.local_storage import LocalStorage
from src.domain.validator import OcrDataValidator
from config.settings import OLLAMA_MODEL
import json


class DocumentProcessor:
    """公文處理協調器 - 整合完整流程"""

    def __init__(self, prompts_path: str):
        self._prompts = self._load_prompts(prompts_path)
        self._ollama = OllamaClient(
            model=OLLAMA_MODEL,
            system_prompt=self._prompts
        )
        self._validator = OcrDataValidator()
        self._storage = LocalStorage()

    def _load_prompts(self, prompts_path: str) -> str:
        """載入 prompts.json 設定"""
        try:
            with open(prompts_path, 'r', encoding='utf-8') as f:
                sys_prompt = json.load(f)
                sys_prompt = json.dumps(sys_prompt,
                                        indent=2, ensure_ascii=False)
                return sys_prompt
        except Exception as e:
            error(f"載入 prompts.json 失敗：{e}")
            warning("將使用預設參數")
            return ""

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
            # 步驟 1: OCR + 欄位提取
            raw_data = await self._ollama.generate(image_path)

            # 解析 JSON 陣列為 dict
            if isinstance(raw_data, list):
                parsed_data = json.loads(raw_data[0]) if raw_data else {}
            else:
                parsed_data = json.loads(raw_data) if raw_data else {}

            # 步驟 2: 驗證資料
            info("執行資料驗證...")
            is_valid, error_code, result = self._validator.validate_and_prepare(
                parsed_data)

            # 步驟 3: 結果回傳
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

    async def process_batch(self, image_paths: list) -> dict:
        """批次處理多張圖片"""
        info(f"批次處理 {len(image_paths)} 張圖片")

        # 並列執行（或根據需求調整為順序執行的 asyncio.gather）
        results = await asyncio.gather(*[
            self.process_single(img) for img in image_paths
        ])

        # 儲存至 CSV
        prepared_data = []
        for r in results:
            # 提取檔名中的編號 (格式: OOOXXX_0001.jpg)
            filename = os.path.basename(r["image_path"])
            base_name = filename.split('_')[0]
            # OOO 是 3 位民國年，XXX 是 3 位流水號，所以取 index 3 到 6
            serial_number = base_name[3:6] if len(base_name) >= 6 else ""

            # 取得解析結果，並將編號注入 csv_data 以便儲存模組寫入 CSV
            csv_data = r.get("result", {}).copy()
            csv_data["serial_number"] = serial_number

            prepared_data.append({
                **r,
                "is_valid": r["success"],
                "csv_data": csv_data,
                "error_code": r.get("error", ""),
                "serial_number": serial_number  # 額外記錄於最外層備用
            })

        batch_count = self._storage.append_batch(prepared_data)

        # 額外產出用於複製的 CSV 檔案 (Overwrite 模式)
        self._storage.save_for_copying(prepared_data)

        info(f"批次處理完成：{batch_count}/{len(image_paths)}")

        return {
            "processed": len(results),
            "success": sum(1 for r in results if r.get("success")),
            "failed": sum(1 for r in results if not r.get("success")),
            "csv_file": str(self._storage._csv_file),
            "results": results
        }


@catch_exception
async def main():
    """CLI 測試程式碼"""
    import argparse

    parser = argparse.ArgumentParser(description="CVTA 公文 OCR 分析器")
    parser.add_argument("--images", nargs="*", help="圖片路徑列表")
    args = parser.parse_args()

    if not args.images:
        print("請提供圖片路徑或建立 .env 檔案")
        sys.exit(1)

    # 建立處理協調器
    processor = DocumentProcessor(
        "E:\\ProgramData\\Repo\\公文系統\\V3\\CVTA-Documents-Analyzer-V3\\config\\prompts.json"
    )

    # 執行批次處理
    result = await processor.process_batch(args.images)

    # 輸出結果
    print("\n=== 處理結果 ===")
    print(f"處理圖片：{result['processed']} 張")
    print(f"成功：{result['success']} 筆")
    print(f"失敗：{result['failed']} 筆")
    print(f"CSV 檔案：{result['csv_file']}")


if __name__ == "__main__":
    asyncio.run(main())
