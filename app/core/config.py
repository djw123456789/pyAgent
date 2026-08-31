from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # 数据库
    DATABASE_URL: str = "sqlite+aiosqlite:///./database.db"

    # Redis 缓存（redis://host:port/db序号）
    REDIS_URL: str = "redis://127.0.0.1:6379/0"
    CACHE_TTL: int = 60  # 缓存默认过期时间（秒）
    
    # JWT 配置（等同于 application.yml 中的 jwt.secret）
    SECRET_KEY: str = "your-secret-key-change-in-production"  # 生产环境务必更换！
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_file = ".env"

settings = Settings()