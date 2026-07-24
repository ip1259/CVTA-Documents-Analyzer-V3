import csv
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.config.settings import DATA_DIR, INPUT_DIR, OUTPUT_DIR
from src.infrastructure.logger import info, warning


class LocalStorage:
    """Store OCR results in local CSV files."""

    CSV_FIELDS = (
        "is_valid",
        "error_code",
        "serial_number",
        "doc_date",
        "doc_category",
        "doc_number",
        "doc_from",
        "case_officer",
        "related_class",
        "key_points",
        "processed_time",
    )
    VALID_DATA_FIELDS = (
        "doc_date",
        "doc_category",
        "doc_number",
        "doc_from",
        "case_officer",
        "related_class",
        "key_points",
    )

    def __init__(self, output_dir: Optional[str | Path] = None):
        project_root = Path(__file__).resolve().parents[2]
        self._output_dir = (
            Path(output_dir)
            if output_dir is not None
            else project_root / DATA_DIR / OUTPUT_DIR
        )
        self._input_dir = project_root / DATA_DIR / INPUT_DIR
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._input_dir.mkdir(parents=True, exist_ok=True)
        self._csv_file = self._output_dir / "ocr_results.csv"

        if not self._csv_file.exists():
            self._init_csv()

    def _init_csv(self) -> None:
        with self._csv_file.open("w", newline="", encoding="utf-8") as file:
            csv.writer(file).writerow(self.CSV_FIELDS)
        info(f"已建立 CSV：{self._csv_file}")

    def append_batch(self, records: list) -> dict:
        stats = {
            "written": 0,
            "valid": 0,
            "invalid": 0,
            "skipped": 0,
            "errors": [],
        }
        if not records:
            return stats

        with self._csv_file.open("a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            for index, record in enumerate(records):
                try:
                    row, is_valid = self._prepare_row(record)
                    writer.writerow(row)
                except Exception as exc:
                    stats["skipped"] += 1
                    stats["errors"].append({
                        "index": index,
                        "error": str(exc),
                    })
                    warning(f"跳過第 {index + 1} 筆 CSV 資料：{exc}")
                    continue

                stats["written"] += 1
                if is_valid:
                    stats["valid"] += 1
                else:
                    stats["invalid"] += 1

        info(
            f"CSV 寫入完成：{stats['written']} 筆，"
            f"跳過 {stats['skipped']} 筆"
        )
        return stats

    def _prepare_row(self, record: object) -> tuple[list[str], bool]:
        if not isinstance(record, dict):
            raise ValueError("record 必須是 dict")
        if not isinstance(record.get("is_valid"), bool):
            raise ValueError("record 缺少布林 is_valid")

        csv_data = record.get("csv_data", {})
        if not isinstance(csv_data, dict):
            raise ValueError("csv_data 必須是 dict")

        is_valid = record["is_valid"]
        if is_valid:
            missing = [
                field
                for field in self.VALID_DATA_FIELDS
                if field not in csv_data
            ]
            if missing:
                raise ValueError(f"有效資料缺少欄位：{', '.join(missing)}")

        return [
            str(is_valid),
            "" if is_valid else str(record.get("error_code", "unknown")),
            str(csv_data.get("serial_number", "")),
            str(csv_data.get("doc_date", "")),
            str(csv_data.get("doc_category", "")),
            str(csv_data.get("doc_number", "")),
            str(csv_data.get("doc_from", "")),
            str(csv_data.get("case_officer", "")),
            str(csv_data.get("related_class", "")),
            str(csv_data.get("key_points", "")),
            datetime.now().isoformat(),
        ], is_valid

    def save_for_copying(self, prepared_data: list) -> None:
        copy_csv = self._output_dir / "ocr_copy_format.csv"
        with copy_csv.open("w", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file)
            writer.writerow([
                "NO.",
                "日期",
                "班級",
                "發文機關",
                "文別",
                "原文字號-字別",
                "原文字號-字",
                "原文字號-文號",
                "原文字號-號",
                "事由",
                "承辦人",
                "備註",
                "公文識別碼",
            ])

            for record in prepared_data:
                csv_data = record.get("csv_data", {})
                if not isinstance(csv_data, dict) or not csv_data:
                    continue

                doc_date = str(csv_data.get("doc_date", ""))
                roc_year = ""
                if len(doc_date) >= 4:
                    try:
                        roc_year = str(int(doc_date[:4]) - 1911)
                    except ValueError:
                        pass
                serial_number = str(
                    csv_data.get("serial_number", "")
                ).zfill(3)
                document_id = f"資職{roc_year}{serial_number}"

                writer.writerow([
                    csv_data.get("serial_number", ""),
                    doc_date,
                    csv_data.get("related_class", ""),
                    csv_data.get("doc_from", ""),
                    "函",
                    csv_data.get("doc_category", ""),
                    "字第",
                    csv_data.get("doc_number", ""),
                    "號",
                    csv_data.get("key_points", ""),
                    csv_data.get("case_officer", ""),
                    "無不可公開",
                    document_id,
                ])

        info(f"已儲存複製格式 CSV：{copy_csv}")

    def export_json(self) -> list[dict]:
        with self._csv_file.open("r", encoding="utf-8") as file:
            return list(csv.DictReader(file))
