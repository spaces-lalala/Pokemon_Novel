import os
from dotenv import load_dotenv
from typing import Optional

# Load environment variables from .env file
load_dotenv()

class Settings:
    """
    Application settings.
    Values are loaded from environment variables.
    """
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    # In the future, we might want to specify the model name via settings
    # OPENAI_MODEL_NAME: str = os.getenv("OPENAI_MODEL_NAME", "gpt-4-turbo-preview")

    # Add other settings as needed

# Instantiate settings to be imported by other modules
settings = Settings()

if __name__ == "__main__":
    # For testing purposes
    if settings.OPENAI_API_KEY:
        print(f"OpenAI API Key loaded: {settings.OPENAI_API_KEY[:5]}...{settings.OPENAI_API_KEY[-4:]}")
    else:
        print("OpenAI API Key not found. Make sure it's set in your .env file.")
    # print(f"Default OpenAI Model: {settings.OPENAI_MODEL_NAME}") 