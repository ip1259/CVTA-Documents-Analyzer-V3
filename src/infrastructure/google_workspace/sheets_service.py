#!/usr/bin/env python3
"""Google Sheets API 服務層 - 公文資料同步至 Google 表格。"""

from typing import Optional
import re
from typing import Any
from googleapiclient.errors import HttpError

from config import settings
from infrastructure.google_workspace import GoogleServiceAccount
from infrastructure.logger import info, error, warning


class GoogleSheetsError(Exception):
    """Google Sheets API 錯誤例外類別。"""


# 表格欄位定義
SHEET_COLUMNS = [
    "NO.",
    "日期",
    "班級",
    "發文機關",
    "文別",
    "原文字號-字別",
    "原文字號-字第",
    "原文字號-文號",
    "原文字號-號",
    "事由",
    "承辦人",
    "單位",
    "公文編號",
]


class GoogleSheetsService:
    """Google Sheets API 服務封裝。"""

    def __init__(self, google_account_service: GoogleServiceAccount, spreadsheet_id: Optional[str] = None):
        """初始化 Google Sheets 服務。

        Args:
            google_account_service: 已認證的 GoogleServiceAccount 實例。
            spreadsheet_id: 指定的 Spreadsheet ID，若未提供則從 settings 讀取。
        """
        self._gs = google_account_service
        if not self._gs.authenticated:
            raise GoogleSheetsError("Google API 服務帳戶未認證")

        self._service = google_account_service.sheets_service
        # 優先使用傳入的 ID，否則尋找設定檔中的 GOOGLE_SPREADSHEET_ID
        self.spreadsheet_id = spreadsheet_id or getattr(
            settings, "GOOGLE_SPREADSHEET_ID", None)

    def append_values(self, values: list[list[str]], sheet_range: str = "Sheet1!A1") -> None:
        """Append 值至 Google Sheets。

        Args:
            values: 二維數組 [][]，內容為要寫入的列資料。
            sheet_range: 寫入的範圍起點。
        """
        if not self.spreadsheet_id:
            error("未設定 Google Spreadsheet ID，無法同步。")
            return

        try:
            info(
                f"正在同步 {len(values)} 筆資料至 Google Sheets (ID: {self.spreadsheet_id})")

            # 執行 Append 操作
            response = self._service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range=sheet_range,
                valueInputOption="USER_ENTERED",
                body={"values": values}
            ).execute()

            # 取得新增加的範圍，並根據該範圍套用前一列的格式
            updated_range = response.get("updates", {}).get("updatedRange")
            if updated_range:
                self._apply_format_from_previous_row(updated_range)

            info("Google Sheets 資料同步成功。")
        except HttpError as e:
            error(f"Google Sheets API 呼叫失敗: {e}")
            raise GoogleSheetsError(f"寫入 Google Sheets 失敗: {e}")
        except Exception as e:
            error(f"同步資料至 Google Sheets 時發生未知錯誤: {e}")
            raise GoogleSheetsError(str(e))

    def _apply_format_from_previous_row(self, range_name: str) -> None:
        """解析產生的範圍並從該範圍的前一列複製格式。"""
        try:
            if "!" not in range_name:
                return

            # 解析範圍字串，例如 "Sheet1!A10:M12"
            sheet_name, cell_range = range_name.split("!")
            sheet_name = sheet_name.strip("'")

            # 使用正則表達式提取所有列號
            row_numbers = [int(n) for n in re.findall(r"\d+", cell_range)]
            if not row_numbers:
                return

            start_row = row_numbers[0]  # 起始列號 (1-based)
            end_row = row_numbers[-1]    # 結束列號

            # 只有當起始列大於 1 時（即上方有其他列），才進行格式複製
            if start_row > 1:
                self._copy_format(sheet_name, start_row, end_row)
        except Exception as e:
            warning(f"自動套用表格格式失敗 (但不影響資料寫入): {e}")

    def _get_sheet_id(self, sheet_name: str) -> int:
        """透過工作表標題取得對應的 sheetId。"""
        spreadsheet = self._service.spreadsheets().get(
            spreadsheetId=self.spreadsheet_id,
            fields="sheets(properties(title,sheetId))"
        ).execute()

        for sheet in spreadsheet.get("sheets", []):
            props = sheet.get("properties", {})
            if props.get("title") == sheet_name:
                return props.get("sheetId")

        raise GoogleSheetsError(f"在 Spreadsheet 中找不到名為 '{sheet_name}' 的工作表")

    def get_sheet_id_by_name(self, sheet_name: str) -> Optional[int]:
        """透過工作表標題取得對應的 sheetId，若找不到則回傳 None。"""
        try:
            return self._get_sheet_id(sheet_name)
        except GoogleSheetsError:
            return None

    def _get_last_row(self, sheet_name: str) -> int:
        """透過讀取 A 欄來取得指定工作表中有資料的最後一列列號 (1-based)。"""
        try:
            # 讀取 A 欄的所有值
            result = self._service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f"'{sheet_name}'!A:A"
            ).execute()

            values = result.get("values", [])
            return len(values)
        except Exception as e:
            error(f"取得工作表 '{sheet_name}' 最後一列列號失敗: {e}")
            # 發生錯誤時回傳 0 或視情況拋出異常
            return -1

    def _copy_format(self, sheet_name: str, start_row: int, end_row: int) -> None:
        """執行格式複製請求。"""
        sheet_id = self._get_sheet_id(sheet_name)

        # Google Sheets API 的 GridRange 是 0-indexed，且 end 是 exclusive (不包含)
        # 來源列 index 為 start_row - 2 (即 A1 序號的前一個列號轉為 index)
        source_row_index = start_row - 2

        requests = [{
            "copyPaste": {
                "source": {
                    "sheetId": sheet_id,
                    "startRowIndex": source_row_index,
                    "endRowIndex": source_row_index + 1
                },
                "destination": {
                    "sheetId": sheet_id,
                    "startRowIndex": start_row - 1,
                    "endRowIndex": end_row
                },
                "pasteType": "PASTE_FORMAT"
            }
        }]

        self._service.spreadsheets().batchUpdate(
            spreadsheetId=self.spreadsheet_id,
            body={"requests": requests}
        ).execute()

    @staticmethod
    def format_sheet_row(row_data: dict[str, Any]) -> list[str]:
        """格式化單一公文資料為表格行 (不含圖檔連結)。"""
        return GoogleSheetsService.format_sheet_row_with_id(row_data, "")

    @staticmethod
    def format_sheet_row_with_id(
        row_data: dict[str, Any], image_id: str
    ) -> list[str]:
        """格式化帶圖檔超連結的表格行。

        Args:
            row_data: 包含 OCR 解析結果與 serial_number 的字典。
            image_id: 該公文圖檔在 Google Drive 的 ID。
        """
        # 1. 處理日期與民國年計算 (資職OOOXXX 中的 OOO)
        doc_date = row_data.get("doc_date", "")
        roc_year_str = ""
        if doc_date and len(doc_date) >= 4:
            try:
                # 西元年 - 1911 = 民國年
                roc_year_str = str(int(doc_date[:4]) - 1911)
            except (ValueError, TypeError):
                pass

        # 2. 處理流水號 (資職OOOXXX 中的 XXX)
        raw_sn = row_data.get("serial_number", "")
        sn_display = str(raw_sn)
        sn_padded = sn_display.zfill(3)

        # 3. 組合公文編號 (格式: 資職OOOXXX)
        doc_id = f"資職{roc_year_str}{sn_padded}"

        # 4. 生成第一欄 NO. 的超連結公式
        # 如果沒有 image_id，則只顯示純數字
        no_cell = GoogleSheetsService.generate_google_drive_link(
            image_id, sn_display)

        # 依照 SHEET_COLUMNS 定義的順序回傳列表
        return [
            no_cell,                          # NO. (Hyperlink)
            doc_date,                         # 日期
            row_data.get("related_class", ""),  # 班級
            row_data.get("doc_from", ""),     # 發文機關
            "函",                             # 文別 (固定值)
            row_data.get("doc_category", ""),  # 原文字號-字別
            "字第",                           # 原文字號-字第
            row_data.get("doc_number", ""),   # 原文字號-文號
            "號",                             # 原文字號-號
            row_data.get("key_points", ""),   # 事由 (摘要)
            row_data.get("case_officer", ""),  # 承辦人
            "中華職訓",                       # 單位 (固定值)
            doc_id                            # 公文編號
        ]

    @staticmethod
    def generate_google_drive_link(file_id: str, display_text: str) -> str:
        """生成 Google Drive 預覽連結的 Sheets 公式。

        Args:
            file_id: Google Drive 檔案 ID。
            display_text: 顯示在儲存格內的文字。
        """
        if not file_id:
            return display_text
        url = f"https://drive.google.com/file/d/{file_id}/view"
        return f'=HYPERLINK("{url}", "{display_text}")'

    def duplicate_sheet(self, sheet_name: str, new_sheet_name: str) -> None:
        """複製工作表。"""
        try:
            sheet_id = self._get_sheet_id(sheet_name)

            requests = [{
                "duplicateSheet": {
                    "sourceSheetId": sheet_id,
                    "newSheetName": new_sheet_name,
                    "insertSheetIndex": 1
                }
            }]

            self._service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body={"requests": requests}
            ).execute()
        except Exception as e:
            error(f"複製工作表失敗: {e}")
            raise GoogleSheetsError(f"複製工作表失敗: {e}")
