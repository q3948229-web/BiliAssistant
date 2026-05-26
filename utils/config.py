from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # App
    APP_NAME: str = "BiliAssistant_Service"
    
    # DashScope
    DASHSCOPE_API_KEY: str
    DASHSCOPE_MODEL: str = "qwen3-asr-flash-filetrans"
    DASHSCOPE_SUMMARY_MODEL: str = "qwen-long"
    
    # Server (replaces OSS — serve files directly for ASR)
    PUBLIC_HOST: str = "http://localhost:8000"
    PUBLIC_DIR: str = "public"
    
    # Paths
    DOWNLOAD_DIR: str = "downloads"
    OUTPUT_DIR: str = "output"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
