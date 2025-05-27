import os
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

class Settings:
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")

settings = Settings()

if __name__ == "__main__":
    if settings.OPENAI_API_KEY:
        print(f"已載入 OpenAI API Key: {settings.OPENAI_API_KEY[:5]}...{settings.OPENAI_API_KEY[-4:]}")
    else:
        print("找不到 OpenAI API Key。請確認已在 .env 檔案中設定。")