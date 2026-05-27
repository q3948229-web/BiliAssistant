from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # App
    APP_NAME: str = "BiliAssistant_Service"
    
    # DashScope (ASR - 语音识别)
    DASHSCOPE_API_KEY: str
    DASHSCOPE_MODEL: str = "qwen3-asr-flash-filetrans"

    # LLM (大语言模型 - 独立配置，可与 ASR 用不同 provider)
    LLM_API_KEY: Optional[str] = None       # 不填则复用 DASHSCOPE_API_KEY
    LLM_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    LLM_MODEL: str = "qwen-long"
    
    # Server (replaces OSS — serve files directly for ASR)
    PUBLIC_HOST: str = "http://localhost:8000"
    PUBLIC_DIR: str = "public"
    
    # Paths
    DOWNLOAD_DIR: str = "downloads"
    OUTPUT_DIR: str = "output"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
