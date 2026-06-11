"""
OutEye Edu 1.0 - 智能教研操作系统
FastAPI后端主应用
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time
import sys
from loguru import logger

from app.core.config import settings, init_directories
from app.api.api_v1.api import api_router
from app.core.database import Base, async_engine
from app.models import User, AnalysisRecord, LessonPlan, LearningRecord, UserFeedback, Document, DocumentChunk, UserBehavior


# 配置日志系统
def setup_logging():
    """配置 loguru 日志系统"""
    # 移除默认处理器
    logger.remove()

    # 控制台输出
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.LOG_LEVEL,
        colorize=True
    )

    # 文件输出
    logger.add(
        settings.LOG_FILE,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=settings.LOG_LEVEL,
        rotation="10 MB",
        retention="30 days",
        compression="zip"
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    setup_logging()
    logger.info("Starting OutEye Edu API...")
    init_directories()

    # 创建数据库表
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database tables created")

    # 启动定时数据清理任务
    import asyncio
    cleanup_task = asyncio.create_task(periodic_cleanup())

    logger.info(f"API server ready at http://{settings.HOST}:{settings.PORT}")
    yield

    # 关闭时执行
    cleanup_task.cancel()
    logger.info("Shutting down OutEye Edu API...")
    await async_engine.dispose()


async def periodic_cleanup():
    """定时数据清理任务"""
    from app.services.data_cleanup import data_cleanup_service

    while True:
        try:
            # 每天执行一次清理
            await asyncio.sleep(86400)  # 24小时
            logger.info("执行定时数据清理...")
            await data_cleanup_service.cleanup_all()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"数据清理失败: {e}")
            await asyncio.sleep(3600)  # 失败后1小时重试


# 创建FastAPI应用
app = FastAPI(
    title="OutEye Edu API",
    description="面向外国语言文学一流学科建设的智能教研操作系统",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# 配置CORS
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002",
    "http://localhost:3003",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:3002",
    "http://127.0.0.1:3003",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录请求日志"""
    start_time = time.time()

    # 处理请求
    response = await call_next(request)

    # 计算处理时间
    process_time = time.time() - start_time

    # 记录日志（不记录敏感路径和健康检查）
    path = request.url.path
    if not path.startswith("/docs") and not path.startswith("/redoc") and path != "/health":
        logger.info(
            f"{request.method} {path} "
            f"status={response.status_code} "
            f"duration={process_time:.4f}s"
        )

    # 添加处理时间到响应头
    response.headers["X-Process-Time"] = str(process_time)

    return response


# 全局异常处理（不泄露内部信息）
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理"""
    logger.error(f"Unhandled exception: {type(exc).__name__}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# 速率限制异常处理
@app.exception_handler(429)
async def rate_limit_handler(request: Request, exc):
    """速率限制异常处理"""
    return JSONResponse(
        status_code=429,
        content={"detail": "请求过于频繁，请稍后再试"}
    )


# 注册路由
app.include_router(api_router, prefix="/api/v1")


# 健康检查
@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "healthy", "version": settings.APP_VERSION}


# 根路径
@app.get("/")
async def root():
    """根路径"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": "面向外国语言文学一流学科建设的智能教研操作系统"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
