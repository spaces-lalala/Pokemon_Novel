from openai import OpenAI
from typing import Optional, Dict, Any, AsyncIterator
import asyncio

from config.settings import settings

class OpenAIConfigError(Exception):
    pass

class LLMService:
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gpt-4.1") -> None:
        resolved_api_key = api_key if api_key is not None else settings.OPENAI_API_KEY
        if not resolved_api_key:
            raise OpenAIConfigError(
                "找不到 OpenAI API key。請在 .env 檔案中設定 OPENAI_API_KEY 或直接傳入參數。"
            )
        
        self.client = OpenAI(api_key=resolved_api_key)
        self.model_name = model_name

    async def generate_text(
        self,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        stream: bool = False,
        **kwargs: Any
    ) -> str:
        if stream:
            pass

        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                stream=stream,
                **kwargs
            )

            if stream:
                full_response_content = ""
                print("警告：串流功能尚未完全實作。如果可用，將返回完整回應，否則返回空值。")
                if hasattr(response, 'choices') and response.choices:
                     return response.choices[0].message.content or ""
                return "[串流回應未完全處理]"
            else:
                return response.choices[0].message.content or ""
        except Exception as e:
            print(f"OpenAI API 呼叫錯誤: {e}")
            raise OpenAIConfigError(f"OpenAI API 呼叫失敗: {e}")

async def main_test() -> None:
    print("測試 LLMService...")
    try:
        llm_service = LLMService(model_name="gpt-4.1")
        
        prompt_text = "將以下英文翻譯成法文: 'Hello, world!'"
        print(f"發送提示: {prompt_text}")
        
        generated_text_non_stream = await llm_service.generate_text(prompt_text, max_tokens=50)
        print(f"生成的文字(非串流):\n{generated_text_non_stream}")

        generated_text_stream = await llm_service.generate_text(prompt_text, max_tokens=50, stream=True)
        print(f"生成的文字(模擬串流呼叫):\n{generated_text_stream}")

    except OpenAIConfigError as e:
        print(f"設定錯誤: {e}")
    except Exception as e:
        print(f"發生意外錯誤: {e}")

if __name__ == "__main__":
    asyncio.run(main_test())