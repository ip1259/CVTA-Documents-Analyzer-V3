import asyncio
import base64
from pathlib import Path
from typing import Any
from httpx import TimeoutException
from src.config import settings
from ollama import AsyncClient, ResponseError
from src.infrastructure.logger import error, debug, info, warning


OLLAMA_HOST = settings.OLLAMA_HOST
DEFAULT_MODEL = settings.OLLAMA_MODEL
HEALTH_TIMEOUT = settings.OLLAMA_HEALTH_TIMEOUT
REQUEST_TIMEOUT = settings.OLLAMA_REQUEST_TIMEOUT

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
        self._client = AsyncClient(
            host=settings.OLLAMA_HOST,
            timeout=settings.OLLAMA_REQUEST_TIMEOUT
        )

    @property
    def model(self) -> str:
        return self._model

    @model.setter
    def model(self, value: str):
        self._model = value

    @staticmethod
    def _model_name(model_info: Any) -> str:
        """Extract a model name from Ollama response objects or dictionaries."""
        if isinstance(model_info, dict):
            return str(model_info.get("model") or model_info.get("name") or "")
        return str(
            getattr(model_info, "model", None)
            or getattr(model_info, "name", None)
            or ""
        )

    async def check_availability(self) -> tuple[bool, str, str]:
        """Check that Ollama is reachable and the configured model exists."""
        try:
            response = await asyncio.wait_for(
                self._client.list(),
                timeout=settings.OLLAMA_HEALTH_TIMEOUT
            )
        except (TimeoutError, TimeoutException):
            message = (
                f"Ollama 服務回應逾時（{HEALTH_TIMEOUT} 秒），請稍後重試。"
            )
            warning(message)
            return False, "SERVICE_TIMEOUT", message
        except ResponseError as exc:
            message = "Ollama API 回傳錯誤，請檢查服務狀態及設定。"
            error(f"{message} 原因：{exc}")
            return False, "SERVICE_ERROR", message
        except Exception as exc:
            message = (
                f"無法連線至 Ollama 服務（{OLLAMA_HOST}），"
                "請確認服務已啟動及連線設定正確。"
            )
            error(f"{message} 原因：{exc}")
            return False, "SERVICE_UNREACHABLE", message

        models = (
            response.get("models", [])
            if isinstance(response, dict)
            else getattr(response, "models", [])
        )
        available_models = {
            self._model_name(model_info) for model_info in (models or [])
        }
        if self.model not in available_models:
            message = (
                f"找不到 Ollama 模型 {self.model}，"
                "請先下載模型或修改模型設定。"
            )
            warning(message)
            return False, "MODEL_NOT_FOUND", message

        info(f"Ollama 服務及模型可用：{self.model}")
        return True, "", ""

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

            if raw.startswith("```json"):
                raw = raw[7:]
                if "\n" in raw:
                    raw = raw[raw.index("\n"):]

            if raw.endswith("```"):
                raw = raw[:-3]

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

            result = await self._client.chat(
                model=self.model,
                messages=messages,
                options={
                    "temperature": 0.0,  # 固定輸出，降低結構化資料的隨機性。
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
            image_path = "E:\\ProgramData\\Repo\\公文系統\\V3\\CVTA-Documents-Analyzer-V3\\tests\\golden_dataset\\115061_0001.jpg"
            result = await client.generate(image_path)
            print("以下是測試結果:\n" + "\n".join(result))
        except Exception as e:
            print(f"測試異常：{e}")
        finally:
            pass

    asyncio.run(run_test())
