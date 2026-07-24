from datetime import date, datetime

from src.config.settings import DATE_VALIDATION_DAYS
from src.infrastructure.logger import error, info, warning


class OcrDataValidator:
    """Validate and normalize OCR output for storage."""

    VALIDATION_ERROR_CODES = {
        "invalid_format": "invalid_format",
        "missing_required_field": "missing_required_field",
        "invalid_date": "invalid_date",
        "invalid_date_window": "invalid_date_window",
        "key_points_invalid_type": "key_points_invalid_type",
        "missing_key_points": "missing_key_points",
    }

    VALID_DATE_WINDOW_DAYS = DATE_VALIDATION_DAYS
    STRING_FIELDS = (
        "doc_date",
        "doc_category",
        "doc_number",
        "doc_from",
        "case_officer",
        "related_class",
    )

    def __init__(self):
        self._current_date = date.today()
        info(f"日期校驗器初始化，當前日期：{self._current_date}")

    def _validate_date_field(self, value: str) -> tuple[bool, str]:
        try:
            normalized = value.strip("\"'")
            document_date = datetime.strptime(
                normalized,
                "%Y-%m-%d"
            ).date()
        except (TypeError, ValueError) as exc:
            error(f"日期格式錯誤 {value}: {exc}")
            return False, self.VALIDATION_ERROR_CODES["invalid_date"]

        days_diff = abs((document_date - self._current_date).days)
        if days_diff > self.VALID_DATE_WINDOW_DAYS:
            warning(
                f"日期 {normalized} 超出允許範圍 "
                f"{self.VALID_DATE_WINDOW_DAYS} 天"
            )
            return (
                False,
                self.VALIDATION_ERROR_CODES["invalid_date_window"],
            )
        return True, ""

    @staticmethod
    def _normalize_key_points(value: object) -> list[str] | None:
        if isinstance(value, str):
            points = [point.strip() for point in value.split(",")]
        elif isinstance(value, list):
            if any(not isinstance(point, str) for point in value):
                return None
            points = [point.strip() for point in value]
        else:
            return None

        normalized = [point for point in points if point]
        return normalized or None

    def _validate_data(self, parsed_data: object) -> tuple[bool, str]:
        info("開始資料驗證流程...")
        if not isinstance(parsed_data, dict):
            return False, self.VALIDATION_ERROR_CODES["invalid_format"]

        for field_name in self.STRING_FIELDS:
            if field_name not in parsed_data:
                warning(f"缺少欄位：{field_name}")
                return (
                    False,
                    self.VALIDATION_ERROR_CODES["missing_required_field"],
                )
            value = parsed_data[field_name]
            if not isinstance(value, str) or not value.strip():
                warning(f"必填欄位無效：{field_name}")
                return (
                    False,
                    self.VALIDATION_ERROR_CODES["missing_required_field"],
                )
            parsed_data[field_name] = value.strip()

        if "key_points" not in parsed_data or parsed_data["key_points"] is None:
            return False, self.VALIDATION_ERROR_CODES["missing_key_points"]

        key_points = self._normalize_key_points(parsed_data["key_points"])
        if key_points is None:
            error_code = (
                "missing_key_points"
                if parsed_data["key_points"] in ("", [])
                else "key_points_invalid_type"
            )
            return False, self.VALIDATION_ERROR_CODES[error_code]
        parsed_data["key_points"] = key_points

        return self._validate_date_field(parsed_data["doc_date"])

    @staticmethod
    def prepare_csv(fields: dict) -> dict:
        key_points = fields.get("key_points", "")
        if isinstance(key_points, list):
            key_points_text = ", ".join(
                point for point in key_points if isinstance(point, str)
            )
        elif isinstance(key_points, str):
            key_points_text = key_points
        else:
            key_points_text = ""

        return {
            "doc_date": fields.get("doc_date", ""),
            "doc_category": fields.get("doc_category", ""),
            "doc_number": fields.get("doc_number", ""),
            "doc_from": fields.get("doc_from", ""),
            "case_officer": fields.get("case_officer", ""),
            "related_class": fields.get("related_class", ""),
            "key_points": key_points_text,
        }

    def validate_and_prepare(
        self,
        raw_data: object
    ) -> tuple[bool, str, dict]:
        try:
            is_valid, error_code = self._validate_data(raw_data)
            prepared = {
                "is_valid": is_valid,
                "error_code": error_code,
                "csv_data": (
                    self.prepare_csv(raw_data)
                    if isinstance(raw_data, dict)
                    else {}
                ),
            }
            if not is_valid:
                warning(f"資料驗證失敗 ({error_code})")
                return False, error_code, prepared

            info("資料驗證通過")
            return True, "", prepared
        except Exception as exc:
            error(f"驗證發生未預期錯誤：{exc}")
            return (
                False,
                "validation_exception",
                {
                    "is_valid": False,
                    "error_code": "validation_exception",
                    "csv_data": {},
                    "error": str(exc),
                },
            )
