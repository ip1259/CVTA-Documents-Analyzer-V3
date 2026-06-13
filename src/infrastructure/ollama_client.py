import asyncio
import base64
from pathlib import Path
from config import settings
from ollama import AsyncClient
from src.infrastructure.logger import error, debug, info, warning


# Ollama API 設定（從 config/settings.py 讀取）
OLLAMA_HOST = settings.OLLAMA_HOST
DEFAULT_MODEL = settings.OLLAMA_MODEL

# System Prompt 規格（可從 config/prompts.json 讀取）
DEFAULT_SYSTEM_PROMPT = """
你是一個公文 OCR 文字辨識與欄位提取專家。

請分析提供的公文圖片，並提取以下欄位：
- doc_date: 公文日期（民國→西元，ISO-8601 格式 YYYY-MM-DD）
- doc_category: 公文分類/字別（例："中分署訓"）
- doc_number: 文號（純數字字串）
- doc_from: 發文機關全銜
- case_officer: 承辦人/聯絡人姓名
- related_class: 班別/專案名稱
- key_points: 關鍵字/摘要（字串陣列）

請務必以純 JSON 格式回覆，禁止包含 ```json 等 Markdown 標記。
請使用 Temperature=0.0 的設定以獲得穩定輸出。
"""


class OllamaClient:
    """Ollama 多模態模型客戶端"""

    def __init__(self, model: str = DEFAULT_MODEL, system_prompt: str = None):
        self._model = model
        self._system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
        self._client = AsyncClient(host=OLLAMA_HOST, timeout=None)

    @property
    def model(self) -> str:
        return self._model

    @model.setter
    def model(self, value: str):
        self._model = value

    async def _encode_image(self, image_path: str) -> str:
        """將圖片檔案轉換為 Base64 編碼"""
        try:
            with Path(image_path).open("rb") as f:
                img_bytes = f.read()
                return base64.b64encode(img_bytes).decode("utf-8")
        except Exception as e:
            error(f"圖片編碼失敗 {image_path}: {e}")
            raise

    def _parse_json_response(self, raw_text: str) -> list:
        """從原始文字中提純 JSON 字串，移除 Markdown 污染"""
        try:
            raw = raw_text.strip()

            # 移除 ```json 等 Markdown 標記
            if raw.startswith("```json"):
                raw = raw[7:]  # 移除 ```json
                if "\n" in raw:
                    raw = raw[raw.index("\n"):]

            if raw.endswith("```"):
                raw = raw[:-3]  # 移除```

            # 嘗試移除前後空白
            raw = raw.strip()

            debug(f"提純後的 JSON: {raw[:200]}...")
            return [raw]

        except Exception as e:
            warning(f"JSON 解析失敗，回傳原始文字：{e}")
            return [raw_text]

    async def generate(self, image_path: str) -> list:
        """
        執行 OCR 解析與欄位提取（非同步方式）

        Args:
            image_path: 公文圖片路徑

        Returns:
            欄位列表 [doc_date, doc_category, doc_number, doc_from, case_officer, related_class, key_points]

        Raises:
            OllamaAPIError: 當 API 調用失敗時
        """
        try:
            encoded = await self._encode_image(image_path)
            messages = [
                {
                    "role": "user",
                    "content": self._system_prompt,
                    "images": [encoded]
                }
            ]

            info(f"呼叫 Ollama API，模型：{self.model}，圖片：{image_path}")

            # 發送請求
            result = await self._client.chat(
                model=self.model,
                messages=messages,
                options={
                    "temperature": 0.0,  # 穩定輸出
                    "top_p": 0.9,
                    "num_predict": 4096
                }
            )

            raw_text = result["message"]["content"]
            parsed = self._parse_json_response(raw_text)

            debug(f"OCR 完成：{result}")
            return parsed

        except Exception as e:
            error(f"Ollama 呼叫失敗：{e}")
            raise

# ============================================
# 測試程式碼
# ============================================


if __name__ == "__main__":
    import json
    sys_prompt = ""
    with open("config/prompts.json", "r", encoding="utf-8") as f:
        sys_prompt = json.load(f)
        sys_prompt = json.dumps(sys_prompt, indent=2, ensure_ascii=False)

    async def run_test():
        client = OllamaClient(
            model=settings.OLLAMA_MODEL,
            system_prompt=sys_prompt
        )

        try:
            # 測試：傳入 tests/golden_dataset 中的第一張圖片
            image_path = "E:\\ProgramData\\Repo\\公文系統\\V3\\CVTA-Documents-Analyzer-V3\\tests\\golden_dataset\\115061_0001.jpg"
            result = await client.generate(image_path)
            print("以下是測試結果:\n" + "\n".join(result))
        except Exception as e:
            print(f"測試異常：{e}")
        finally:
            pass

    asyncio.run(run_test())
