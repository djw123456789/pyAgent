from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # 数据库
    DATABASE_URL: str = "sqlite+aiosqlite:///./database.db"

    # Redis 缓存
    REDIS_URL: str = "redis://8.148.9.192:6379/0"
    CACHE_TTL: int = 60

    # Celery
    CELERY_BROKER_URL: str = "amqp://admin:123456@8.148.9.192:5672//"
    CELERY_RESULT_BACKEND: str = "redis://8.148.9.192:6379/1"

    # DeepSeek
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-v4-flash"

    # JWT
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_file = ".env"

settings = Settings()