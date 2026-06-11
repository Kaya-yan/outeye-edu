"""
OutEye Edu 配置文件
"""

from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    """应用配置"""

    # 应用基础配置
    APP_NAME: str = "OutEye Edu"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # 安全密钥（必需，无默认值）
    SECRET_KEY: str

    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # 数据库配置
    DATABASE_URL: str
    DB_ECHO: bool = False

    # Redis配置
    REDIS_URL: str

    # Qdrant配置
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION: str = "outeye_knowledge"

    # LLM配置
    LLM_PROVIDER: str = "deepseek"
    LLM_API_KEY: str
    LLM_BASE_URL: str = "https://api.deepseek.com"
    LLM_MODEL: str = "deepseek-chat"
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 2000

    # Embedding模型配置
    EMBEDDING_MODEL: str = "bge-large-zh-v1.5"
    EMBEDDING_DIMENSION: int = 1024

    # CORS配置
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # JWT配置
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 120

    # 文件上传配置
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".docx", ".txt", ".md"]

    # Mimo API配置（可选）
    MIMO_API_KEY: Optional[str] = None
    MIMO_API_URL: Optional[str] = None

    # 前端配置（可选）
    NEXT_PUBLIC_API_URL: Optional[str] = None

    # 管理员邮箱（可选）
    ADMIN_EMAIL: Optional[str] = None

    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/outeye.log"

    # 性能配置
    WORKERS: int = 4
    MAX_CONCURRENT_REQUESTS: int = 100

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# 创建全局设置实例
settings = Settings()


def init_directories():
    """初始化必要的目录（在应用启动时调用）"""
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs("logs", exist_ok=True)