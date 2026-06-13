import asyncio
from src.infrastructure.logger import info, warning
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
import os
import csv
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class LocalStorage:
    """本地 CSV 儲存器（Append 模式，使用 config 目錄中的設定）"""

    def __init__(self, output_dir: Optional[str] = None):
        # 從設定檔讀取目錄設定
        try:
            sys.path.insert(0, os.path.dirname(
                os.path.dirname(os.path.dirname(__file__))))
            from config.settings import DATA_DIR, INPUT_DIR, OUTPUT_DIR

            base_path = Path(__file__).parent.parent.parent
            self._output_dir = base_path / DATA_DIR / OUTPUT_DIR
            self._input_dir = base_path / DATA_DIR / INPUT_DIR
            self._output_dir.mkdir(parents=True, exist_ok=True)
            self._input_dir.mkdir(parents=True, exist_ok=True)
            self._csv_file = self._output_dir / "ocr_results.csv"
        except ImportError:
            # 預設路徑
            self._output_dir = Path(output_dir) if output_dir else Path(
                "data/output_results")
            self._input_dir = Path("data/input_scans")
            self._output_dir.mkdir(parents=True, exist_ok=True)
            self._input_dir.mkdir(parents=True, exist_ok=True)
            self._csv_file = self._output_dir / "ocr_results.csv"

        # 確保 CSV 存在（如無則建立表頭）
        if not self._csv_file.exists():
            self._init_csv()

    def _init_csv(self):
        """建立 CSV 表頭"""
        with open(self._csv_file, 'a+', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # 表頭（包含是否驗證成功）
            writer.writerow([
                "is_valid",  # 驗證狀態
                "error_code",  # 錯誤代碼
                "serial_number",  # 檔案編號 (XXX)
                "doc_date", "doc_category", "doc_number",
                "doc_from", "case_officer", "related_class", "key_points",
                "processed_time"  # 處理時間
            ])
            info(f"CSV 檔案已建立：{self._csv_file}")

    def append_batch(self, raw_data: list) -> List[int]:
        """
        批次追加記錄

        Args:
            raw_data: [{"is_valid": bool, "error_code": str, "csv_data": dict}, ...]

        Returns:
            成功追加的筆數
        """
        if not raw_data:
            warning("無資料可儲存")
            return 0

        success_count = 0

        with open(self._csv_file, 'a+', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            for record in raw_data:
                if record["is_valid"]:
                    csv_data = record["csv_data"]
                    processed_row = [
                        "True",         # is_valid
                        "",              # error_code
                        csv_data.get("serial_number", ""),
                        csv_data["doc_date"],
                        csv_data["doc_category"],
                        csv_data["doc_number"],
                        csv_data["doc_from"],
                        csv_data["case_officer"],
                        csv_data["related_class"],
                        str(csv_data["key_points"]),
                        datetime.now().isoformat()  # processed_time
                    ]
                    writer.writerow(processed_row)
                    success_count += 1

                elif record["is_valid"] is False:
                    csv_data = record.get("csv_data", {})
                    processed_row = [
                        "False",         # is_valid
                        record.get("error_code", "unknown"),
                        csv_data.get("serial_number", ""),
                        csv_data.get("doc_date", ""),
                        csv_data.get("doc_category", ""),
                        csv_data.get("doc_number", ""),
                        csv_data.get("doc_from", ""),
                        csv_data.get("case_officer", ""),
                        csv_data.get("related_class", ""),
                        csv_data.get("key_points", ""),
                        datetime.now().isoformat()
                    ]
                    writer.writerow(processed_row)
                    warning(
                        f"錯誤記錄：{record['error_code']} - {record.get('csv_data', {})}")
                    success_count += 1

        info(f"成功追加{success_count}筆記錄")
        return success_count

    def save_for_copying(self, prepared_data: list):
        """
        產出供快速複製使用的 CSV 格式 (Overwrite 模式)
        結構包含 13 欄位，包含合併字號拆分與民國年公文編號
        """
        copy_csv = self._output_dir / "ocr_copy_format.csv"

        try:
            with open(copy_csv, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                # 寫入表頭 (對應使用者提供的結構)
                writer.writerow([
                    "NO.", "日期", "班級", "發文機關", "文別",
                    "原文字號-字別", "原文字號-字第", "原文字號-文號", "原文字號-號",
                    "事由", "承辦人", "單位", "公文編號"
                ])

                for record in prepared_data:
                    # 僅處理成功驗證或有資料的記錄
                    csv_data = record.get("csv_data", {})
                    if not csv_data:
                        continue

                    # 1. 處理日期與民國年計算
                    doc_date = csv_data.get("doc_date", "")
                    roc_year_str = ""
                    if doc_date and len(doc_date) >= 4:
                        try:
                            roc_year_str = str(int(doc_date[:4]) - 1911)
                        except ValueError:
                            pass

                    # 2. 處理流水號補零
                    sn = str(csv_data.get("serial_number", "")).zfill(3)

                    # 3. 組合公文編號 (格式: 資職OOOXXX)
                    doc_id = f"資職{roc_year_str}{sn}"

                    row = [
                        csv_data.get("serial_number", ""),  # NO.
                        doc_date,                         # 日期
                        csv_data.get("related_class", ""),  # 班級
                        csv_data.get("doc_from", ""),     # 發文機關
                        "函",                             # 文別 (固定值)
                        csv_data.get("doc_category", ""),  # 原文字號-字別
                        "字第",                           # 原文字號-字第
                        csv_data.get("doc_number", ""),   # 原文字號-文號
                        "號",                             # 原文字號-號
                        csv_data.get("key_points", ""),   # 事由 (摘要)
                        csv_data.get("case_officer", ""),  # 承辦人
                        "中華職訓",                       # 單位 (固定值)
                        doc_id                            # 公文編號 (資職OOOXXX)
                    ]
                    writer.writerow(row)
            info(f"複製用 CSV 已更新：{copy_csv}")
        except Exception as e:
            warning(f"儲存複製格式 CSV 失敗: {e}")

    def export_json(self) -> List[Dict]:
        """導出為 JSON 陣列"""
        records = []
        with open(self._csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append(row)
        return records


async def main():
    """測試程式碼"""

    # Mock 解析器
    async def mock_parse(image_path):
        """Mock 回傳測試數據"""
        return {
            "doc_date": "2026-04-17",
            "doc_category": "中分署訓",
            "doc_number": "1152301262",
            "doc_from": "勞動部勞動力發展署中彰投分署",
            "case_officer": "張三",
            "related_class": "AI多媒體班",
            "key_points": ["技能檢定", "資格認證", "訓練課程", "就業輔導"]
        }

    # 測試流程
    images = [
        "E:\\ProgramData\\Repo\\公文系統\\V3\\CVTA-Documents-Analyzer-V3\\tests\\golden_dataset\\115064_0001.jpg",
        "E:\\ProgramData\\Repo\\公文系統\\V3\\CVTA-Documents-Analyzer-V3\\tests\\golden_dataset\\115065_0001.jpg"
    ]

    # 模擬批次解析
    raw_results = await asyncio.gather(*[mock_parse(img) for img in images])

    # 驗證並追加
    storage = LocalStorage()

    # 模擬 Orchestrator 的資料準備邏輯，包含提取檔名中的編號
    prepared_data = []
    for img, raw_data in zip(images, raw_results):
        filename = os.path.basename(img)
        base_name = filename.split('_')[0]
        # OOO 是 3 位民國年，XXX 是 3 位流水號，所以取 index 3 到 6
        serial_number = base_name[3:6] if len(base_name) >= 6 else ""

        csv_data = raw_data.copy()
        csv_data["serial_number"] = serial_number

        prepared_data.append({
            "is_valid": True,
            "error_code": "",
            "csv_data": csv_data
        })

    success = storage.append_batch(prepared_data)
    storage.save_for_copying(prepared_data)

    print(f"批次處理完成：{success}/{len(images)}")


if __name__ == "__main__":
    asyncio.run(main())
