# -*- coding: utf-8 -*-
"""CLI 介面 - 批次選檔與 OCR 處理主程式"""

import sys
from pathlib import Path
from tkinter import messagebox, filedialog
import asyncio
from src.config.settings import DATA_DIR, OUTPUT_DIR, VERSION
from src.infrastructure.logger import catch_exception, info, initialize_logging


@catch_exception
def main():
    initialize_logging()
    """主程式入口 - 批次選檔處理"""
    info("===== CVTA 公文 OCR 歸納系統 =====")
    info(f"系統版本：{VERSION if 'VERSION' in globals() else '3.0.0'}")

    file_paths = filedialog.askopenfilenames(
        title="選取公文掃描檔 (可多選)",
        filetypes=[("圖片檔案", "*.jpg *.jpeg *.png"), ("所有檔案", "*.*")]
    )

    if not file_paths:
        info("使用者取消選檔")
        sys.exit(0)

    file_list = list(file_paths)
    info(f"選取檔案數量：{len(file_list)}")
    info(f"儲存目錄：{Path(__file__).parent.parent.parent / DATA_DIR / OUTPUT_DIR}")

    from src.domain.orchestrator import DocumentProcessor

    processor = DocumentProcessor(
        prompts_path="config/prompts.json"
    )

    result = asyncio.run(processor.process_batch(file_list))

    if result.get("service_error"):
        service_error = result["service_error"]
        messagebox.showerror(
            "AI 服務確認失敗",
            f"[{service_error['error_code']}]\n"
            f"{service_error['message']}"
        )
        sys.exit(1)

    if result["success"] > 0 or result["failed"] == 0:
        info(f"批次處理完成：成功 {result['success']} 筆, 失敗 {result['failed']} 筆")
        info(f"CSV 檔案：{result['csv_file']}")
        messagebox.showinfo(
            "處理完成",
            f"任務執行完畢！\n\n總計：{result['processed']} 筆\n成功：{result['success']} 筆\n失敗：{result['failed']} 筆\n\n儲存位置：\n{result['csv_file']}"
        )
    else:
        messagebox.showerror(
            "處理失敗",
            f"所有圖片處理均失敗，共 {result['failed']} 筆。\n\n請檢查 Ollama 服務是否運行或圖片格式是否正確。"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
