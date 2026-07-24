"""公文資料模型 - 搭配 data_storage 與 doc_controller 使用。

本模組提供一個簡單的公文資料模型，支援：
- 欄位定義（dataclass）
- 轉成字典存取（to_dict / from_dict）

設計原則：不過度設計，僅提供必要 API，讓各層自行決定如何呼叫。
"""

from dataclasses import dataclass


@dataclass
class Document:
    """公文資料模型。

    Attributes:
        serial_number: 流水號（唯一識別碼）。
        doc_date: 公文日期（ISO-8601 格式，YYYY-MM-DD）。
        related_class: 相關班級。
        doc_from: 發文機關全銜。
        doc_category: 字別。
        doc_number: 文號（純數字）。
        key_points: 事由（逗號分隔字串）。
        case_officer: 承辦人。
        image_source: 影像來源路徑。
        analyzed: 是否已分析（True 表示已分析）。
        drive_file_id: 雲端硬碟檔案 ID。
    """

    serial_number: str = ""
    doc_date: str = ""
    related_class: str = ""
    doc_from: str = ""
    doc_category: str = ""
    doc_number: str = ""
    key_points: str = ""
    case_officer: str = ""
    image_source: str = ""
    analyzed: bool = False
    drive_file_id: str = ""

    def to_dict(self) -> dict:
        """轉成字典。"""
        return {
            "serial_number": self.serial_number,
            "doc_date": self.doc_date,
            "related_class": self.related_class,
            "doc_from": self.doc_from,
            "doc_category": self.doc_category,
            "doc_number": self.doc_number,
            "key_points": self.key_points,
            "case_officer": self.case_officer,
            "image_source": self.image_source,
            "analyzed": self.analyzed,
            "drive_file_id": self.drive_file_id,
        }

    def update(self, data: dict) -> None:
        """更新公文物件屬性。"""
        if "serial_number" in data:
            self.serial_number = data["serial_number"]
        if "doc_date" in data:
            self.doc_date = data["doc_date"]
        if "related_class" in data:
            self.related_class = data["related_class"]
        if "doc_from" in data:
            self.doc_from = data["doc_from"]
        if "doc_category" in data:
            self.doc_category = data["doc_category"]
        if "doc_number" in data:
            self.doc_number = data["doc_number"]
        if "key_points" in data:
            self.key_points = data["key_points"]
        if "case_officer" in data:
            self.case_officer = data["case_officer"]

    @classmethod
    def from_dict(cls, data: dict) -> "Document":
        """從字典建立公文物件。"""
        if not data.get("image_source"):
            raise ValueError("[ERROR] 建立公文物件失敗，image_source 欄位為空值")

        return cls(
            serial_number=data.get("serial_number", ""),
            doc_date=data.get("doc_date", ""),
            related_class=data.get("related_class", ""),
            doc_from=data.get("doc_from", ""),
            doc_category=data.get("doc_category", ""),
            doc_number=data.get("doc_number", ""),
            key_points=data.get("key_points", ""),
            case_officer=data.get("case_officer", ""),
            image_source=data.get("image_source"),
            analyzed=data.get("analyzed", False),
            drive_file_id=data.get("drive_file_id", ""),
        )


__all__ = ["Document"]
