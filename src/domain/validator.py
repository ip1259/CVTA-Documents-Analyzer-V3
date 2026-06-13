import json
from datetime import datetime, date

from src.infrastructure.logger import info, warning, error, catch_exception

# from src.infrastructure.ollama_client import OllamaClient

from config.settings import DATE_VALIDATION_DAYS


class OcrDataValidator:
    """OCR 解析結果資料驗證器（使用 config/settings.py 中的 DATE_VALIDATION_DAYS）"""

    VALIDATION_ERROR_CODES = {
        "invalid_format": "資料格式錯誤",
        "missing_required_field": "缺少必要欄位",
        "invalid_date": "日期格式錯誤",
        "invalid_date_window": f"日期超出安全閾值 ({DATE_VALIDATION_DAYS} 天)",
        "key_points_not_array": "key_points 必須為陣列",
        "missing_key_points": "缺少 key_points 欄位",
    }

    # 從設定檔讀取日期校驗閾值
    VALID_DATE_WINDOW_DAYS = DATE_VALIDATION_DAYS

    REQUIRED_FIELDS = [
        "doc_date", "doc_category", "doc_number",
        "doc_from", "case_officer", "related_class", "key_points"
    ]

    def __init__(self):
        self._current_date = date.today()
        info(f"日期校驗器初始化，當前日期：{self._current_date}")

    @staticmethod
    def _validate_field_type(fields: dict, field_name: str, expected_type: type):
        """驗證欄位型態（容許 None 和字串型別，因為 Ollama 可能回傳字串）"""
        if field_name not in fields:
            warning(f"缺少欄位：{field_name}")
            return False

        field_data = fields[field_name]

        if field_data is None:
            warning(f"欄位 {field_name} 為 None")
            return True

        # 容許字串或 list 作為 key_points（如果 Ollama 回傳字串）
        if field_name == "key_points" and isinstance(field_data, str):
            return True  # 陣列→字串的轉換會在 validate_and_prepare 階段處理

        if not isinstance(field_data, expected_type):
            expected = expected_type.__name__
            actual = type(field_data).__name__
            warning(f"欄位 {field_name} 型態不符：期待{expected}, 實際{actual}")
            return False

        return True

    def _validate_date_field(self, doc_date_str: str) -> bool:
        """驗證日期欄位格式與時窗（使用設定檔的 DATE_VALIDATION_DAYS）"""
        try:
            # 去除可能的外層引號
            if doc_date_str.startswith('"') or doc_date_str.startswith("'"):
                doc_date_str = doc_date_str.strip('"\'')

            # 嘗試 ISO format
            doc_date = datetime.strptime(doc_date_str, "%Y-%m-%d").date()
            days_diff = abs((doc_date - self._current_date).days)

            if days_diff > self.VALID_DATE_WINDOW_DAYS:
                warning(
                    f"日期 {doc_date_str} 超出安全閾值{self.VALID_DATE_WINDOW_DAYS}天")
                return False

            return True
        except Exception as e:
            error(f"日期驗證失敗 {doc_date_str}: {e}")
            return False

    def _summarize_key_points_array(self, key_points: list) -> str:
        """將 key_points 陣列轉換為逗號分隔字串"""
        if not key_points:
            return ""
        return ", ".join([p.strip() for p in key_points if p])

    def prepare_csv(self, fields: dict) -> dict:
        """調整欄位以符合 CSV 儲存需求"""
        result = {}

        # 基本欄位直接複製
        basic_fields = [
            "doc_date", "doc_category", "doc_number",
            "doc_from", "case_officer", "related_class"
        ]
        for field in basic_fields:
            if field in fields:
                result[field] = fields[field]

        # key_points 特殊處理：陣列 → 字串
        if "key_points" in fields and isinstance(fields["key_points"], list):
            result["key_points"] = self._summarize_key_points_array(
                fields["key_points"])
        elif "key_points" not in fields or fields["key_points"] == "":
            result["key_points"] = ""

        return result

    def _validate_data(self, parsed_data: dict) -> tuple[bool, str]:
        """
        全面驗證解析結果

        Returns:
            (is_valid, error_code) - is_valid 為 False 時 error_code 包含錯誤訊息
        """
        info("開始資料驗證流程...")

        # 1. 基本欄位型別驗證
        if not self._validate_field_type(parsed_data, "doc_date", str):
            return False, self.VALIDATION_ERROR_CODES["missing_required_field"]

        if not self._validate_field_type(parsed_data, "doc_category", str):
            return False, self.VALIDATION_ERROR_CODES["missing_required_field"]

        if not self._validate_field_type(parsed_data, "doc_number", str):
            return False, self.VALIDATION_ERROR_CODES["missing_required_field"]

        if not self._validate_field_type(parsed_data, "doc_from", str):
            return False, self.VALIDATION_ERROR_CODES["missing_required_field"]

        if not self._validate_field_type(parsed_data, "case_officer", str):
            return False, self.VALIDATION_ERROR_CODES["missing_required_field"]

        if not self._validate_field_type(parsed_data, "related_class", str):
            return False, self.VALIDATION_ERROR_CODES["missing_required_field"]

        # 2. key_points 必須存在（容許字串陣列或字串）
        key_points = parsed_data.get("key_points", None)
        if key_points is None:
            warning("缺少 key_points 欄位")
            return False, self.VALIDATION_ERROR_CODES["missing_key_points"]

        # 容許字串型的 key_points（Ollama 可能回傳）
        if isinstance(key_points, str):
            # 用逗號分隔處理
            key_points_list = [p.strip()
                               for p in key_points.split(",") if p.strip()]
            parsed_data["key_points"] = key_points_list

        # 3. 日期格式與閾值（使用設定檔的 90 天）
        if not self._validate_date_field(parsed_data["doc_date"]):
            return False, self.VALIDATION_ERROR_CODES["invalid_date_window"]

        return True, ""

    @catch_exception
    def validate_and_prepare(self, raw_data: dict) -> tuple[bool, str, dict]:
        """
        一鍵處理驗證 + 預備 CSV

        Returns:
            (is_valid, error_code, prepared_data)
        """
        try:
            is_valid, error_code = self._validate_data(raw_data)
            error_msg = error_code if error_code else ""

            # 即使驗證失敗也準備 CSV（但不包含錯誤資料）
            prepared = {"is_valid": is_valid, "error_code": error_code}
            if is_valid:
                prepared["csv_data"] = self.prepare_csv(raw_data)

            if not is_valid:
                warning(f"資料驗證失敗 ({error_code})")
                return False, error_msg, prepared

            info("資料驗證通過")
            return True, "", prepared

        except Exception as e:
            error(f"驗證過程異常：{e}")
            return False, "validation_exception", {"is_valid": False, "error": str(e)}


def main():
    """測試程式碼"""

    # 模擬 OCR 解析器 (同步即可，因為此處僅測試驗證邏輯)
    def mock_parse(image_path: str):
        # Mock 回傳測試數據
        return {
            "doc_date": "2026-04-17",
            "doc_category": "中分署訓",
            "doc_number": "1152301262",
            "doc_from": "勞動部勞動力發展署中彰投分署",
            "case_officer": "張三",
            "related_class": "技能檢定",
            "key_points": ["技能檢定", "資格認證", "訓練課程", "就業輔導"]
        }

    # 模擬圖片路徑
    image_path = "E:\\ProgramData\\Repo\\公文系統\\V3\\CVTA-Documents-Analyzer-V3\\tests\\golden_dataset\\115064_0001.jpg"

    try:
        # 解析單張公文圖片
        raw_data = mock_parse(image_path)

        # 驗證並準備 CSV
        validator = OcrDataValidator()
        is_valid, error_code, prepared = validator.validate_and_prepare(
            raw_data)

        if is_valid:
            print(json.dumps(prepared["csv_data"],
                  indent=2, ensure_ascii=False))
        else:
            print(f"驗證失敗：{error_code}")
    except Exception as e:
        print(f"測試失敗：{e}")
        raise


if __name__ == "__main__":
    main()
