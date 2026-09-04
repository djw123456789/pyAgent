from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # 数据库
    DATABASE_URL: str = "sqlite+aiosqlite:///./database.db"

    # Redis 缓存
    REDIS_URL: str = "redis://127.0.0.1:6379/0"
    CACHE_TTL: int = 60

    # Celery
    CELERY_BROKER_URL: str = "amqp://pyagent:123456@127.0.0.1:5672//"
    CELERY_RESULT_BACKEND: str = "redis://127.0.0.1:6379/1"

    # JWT
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_file = ".env"

settings = Settings()