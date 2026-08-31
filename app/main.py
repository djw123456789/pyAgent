from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlmodel import SQLModel, create_engine
from app.api.v1 import heroes, auth, users  # 导入新路由
from app.core.config import settings
from app.core.cache import redis_client, close_redis
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from fastapi.middleware.cors import CORSMiddleware
from app.middleware.logging import LoggingMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.core.exceptions import (
    AppException,
    app_exception_handler,
    validation_exception_handler,
    sqlalchemy_exception_handler,
    generic_exception_handler
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期: yield 之前=启动时执行, yield 之后=关闭时执行"""
    # --- 启动阶段 ---
    # 1. 启动时先 ping Redis, 连不上立刻报错(fail fast), 不要等到第一个请求才才发现
    pong = await redis_client.ping()
    print(f"[startup] Redis 连接成功: {pong}")

    # 2. 建表(临时用同步引擎, 后续章节换成 Alembic 托管)
    sync_engine = create_engine(settings.DATABASE_URL.replace("+aiosqlite", ""), echo=False)
    SQLModel.metadata.create_all(sync_engine)
    sync_engine.dispose()

    yield  # --- 应用运行中 ---

    # --- 关闭阶段 ---
    await close_redis()
    print("[shutdown] Redis 连接池已释放")

app = FastAPI(title="企业级英雄API", version="4.1.0", lifespan=lifespan)

# 注册路由
app.include_router(heroes.router, prefix="/api/v1/heroes", tags=["英雄管理"])
app.include_router(auth.router, prefix="/api/v1", tags=["认证"])
app.include_router(users.router, prefix="/api/v1", tags=["用户管理"])

# 注册异常处理器
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# 注册限流中间件（放在其他中间件之前，以免被日志等占用请求计数）
app.add_middleware(RateLimitMiddleware, calls_per_minute=10)

# 配置跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应替换为具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(LoggingMiddleware)

