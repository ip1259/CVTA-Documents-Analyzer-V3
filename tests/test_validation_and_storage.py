import csv
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from src.domain.validator import OcrDataValidator
from src.infrastructure.local_storage import LocalStorage


def valid_document() -> dict:
    return {
        "doc_date": date.today().isoformat(),
        "doc_category": "中分署訓",
        "doc_number": "1152301262",
        "doc_from": "勞動力發展署",
        "case_officer": "王小明",
        "related_class": "測試班",
        "key_points": ["測試"],
    }


class OcrDataValidatorTests(unittest.TestCase):
    def setUp(self):
        self.validator = OcrDataValidator()

    def test_required_string_cannot_be_empty(self):
        document = valid_document()
        document["doc_from"] = " "

        valid, error_code, _ = self.validator.validate_and_prepare(document)

        self.assertFalse(valid)
        self.assertEqual("missing_required_field", error_code)

    def test_key_points_accepts_comma_separated_string(self):
        document = valid_document()
        document["key_points"] = "第一點, 第二點"

        valid, _, prepared = self.validator.validate_and_prepare(document)

        self.assertTrue(valid)
        self.assertEqual("第一點, 第二點", prepared["csv_data"]["key_points"])

    def test_key_points_rejects_invalid_types(self):
        for value in (123, {"point": "x"}, True, ["ok", 1], [], ""):
            with self.subTest(value=value):
                document = valid_document()
                document["key_points"] = value
                valid, _, _ = self.validator.validate_and_prepare(document)
                self.assertFalse(valid)

    def test_date_over_90_days_is_invalid(self):
        document = valid_document()
        document["doc_date"] = (
            date.today() - timedelta(days=91)
        ).isoformat()

        valid, error_code, _ = self.validator.validate_and_prepare(document)

        self.assertFalse(valid)
        self.assertEqual("invalid_date_window", error_code)

    def test_date_at_90_day_boundary_is_valid(self):
        document = valid_document()
        document["doc_date"] = (
            date.today() - timedelta(days=90)
        ).isoformat()

        valid, _, _ = self.validator.validate_and_prepare(document)

        self.assertTrue(valid)


class LocalStorageTests(unittest.TestCase):
    def test_output_dir_takes_precedence(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = LocalStorage(output_dir=temp_dir)
            self.assertEqual(
                Path(temp_dir).resolve(),
                storage._output_dir.resolve()
            )

    def test_batch_skips_malformed_record_and_writes_other_rows(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = LocalStorage(output_dir=temp_dir)
            valid_csv_data = {
                **valid_document(),
                "key_points": "測試",
                "serial_number": "001",
            }
            stats = storage.append_batch([
                {
                    "is_valid": True,
                    "error_code": "",
                    "csv_data": valid_csv_data,
                },
                {"is_valid": True, "csv_data": {}},
                {
                    "is_valid": False,
                    "error_code": "missing_required_field",
                    "csv_data": {"doc_from": ""},
                },
            ])

            self.assertEqual(2, stats["written"])
            self.assertEqual(1, stats["valid"])
            self.assertEqual(1, stats["invalid"])
            self.assertEqual(1, stats["skipped"])
            self.assertEqual(1, len(stats["errors"]))

            with storage._csv_file.open(
                "r",
                newline="",
                encoding="utf-8"
            ) as file:
                rows = list(csv.DictReader(file))
            self.assertEqual(2, len(rows))
            self.assertEqual("False", rows[1]["is_valid"])
            self.assertEqual(
                "missing_required_field",
                rows[1]["error_code"]
            )


if __name__ == "__main__":
    unittest.main()
