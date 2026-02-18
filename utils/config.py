from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # App
    APP_NAME: str = "MP3_TO_TXT_Service"
    
    # DashScope
    DASHSCOPE_API_KEY: str
    DASHSCOPE_MODEL: str = "qwen3-asr-flash-filetrans"
    DASHSCOPE_SUMMARY_MODEL: str = "qwen-long"
    
    # OSS
    OSS_ACCESS_KEY_ID: str
    OSS_ACCESS_KEY_SECRET: str
    OSS_ENDPOINT: str
    OSS_BUCKET_NAME: str
    
    # Paths
    DOWNLOAD_DIR: str = "downloads"
    OUTPUT_DIR: str = "output"

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

settings = Settings()
