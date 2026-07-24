"""公文資料表格模型 - 整合 Document 與 DocController（唯讀版）。

本模組提供一個 QAbstractTableModel，每行對應一個 Document 物件。
表格欄位採用特定業務邏輯格式化（如原文字號合併、流水號與檔名切換）。
"""

from typing import List, Any

from PySide6.QtCore import (
    QAbstractTableModel,
    Qt,
    QModelIndex,
)

from src.infrastructure.document import Document


class DocumentTableModel(QAbstractTableModel):
    """公文資料表格模型（唯讀展示用）。"""

    def __init__(self, documents: List[Document], controller=None):
        super().__init__()
        self._documents = documents
        self._controller = controller

        self._headers = [
            "NO.",
            "日期",
            "班級",
            "發文機關",
            "原文字號",
            "事由",
            "承辦人"
        ]

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._documents)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._headers)

    def _is_doc_complete(self, doc: Document) -> bool:
        """檢查公文核心資料欄位是否皆有值（排除已分析標記與雲端ID）。"""
        core_fields = [
            doc.serial_number,
            doc.doc_date,
            doc.related_class,
            doc.doc_from,
            doc.doc_category,
            doc.doc_number,
            doc.key_points,
            doc.case_officer
        ]
        return all(bool(str(field).strip()) for field in core_fields)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid():
            return None

        row = index.row()
        col = index.column()

        if row >= len(self._documents):
            return None

        doc = self._documents[row]

        if role == Qt.DisplayRole:
            if col == 0:
                return doc.serial_number if self._is_doc_complete(doc) else f"!{doc.serial_number}!"

            elif col == 1:
                return doc.doc_date

            elif col == 2:
                return doc.related_class

            elif col == 3:
                return doc.doc_from

            elif col == 4:
                category = doc.doc_category.strip()
                number = doc.doc_number.strip()
                if category or number:
                    return f"{category}字第{number}號"
                return ""

            elif col == 5:
                return doc.key_points

            elif col == 6:
                return doc.case_officer

        elif role == Qt.TextAlignmentRole:
            if col in [0, 1, 2, 4, 6]:
                return Qt.AlignCenter
            return Qt.AlignLeft | Qt.AlignVCenter

        return None

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole
    ) -> Any:
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if 0 <= section < len(self._headers):
                return self._headers[section]
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid():
            return Qt.ItemFlags()
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def refresh_all(self) -> None:
        """當外部表單修改完資料並儲存至後端後，由 Controller 呼叫此方法重新整理視圖。"""
        self.beginResetModel()
        self.endResetModel()
