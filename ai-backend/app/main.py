"""
نقطة تشغيل التطبيق — يجمع كل الطبقات: قاعدة البيانات، CORS، والمسارات (routers)
"""
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

# استيراد models لضمان تسجيلها في Base.metadata (يحتاجها Alembic --autogenerate)
import app.models  # noqa: F401
from app.auth.routes import router as auth_router
from app.auth.two_factor import router as two_factor_router
from app.config import settings
from app.database import get_db
from app.middleware import AuthRateLimitMiddleware, RequestIdMiddleware
from app.logging_config import configure_logging, get_logger
from app.routers.admin import router as admin_router
from app.routers.billing import router as billing_router
from app.routers.chat import router as chat_router
from app.routers.conversations import router as conversations_router
from app.routers.files import router as files_router
from app.routers.notifications import router as notifications_router
from app.routers.users import router as users_router

configure_logging()
logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # الجداول تُدار الآن عبر Alembic (migrations/) مو create_all —
    # شغّل "alembic upgrade head" قبل تشغيل السيرفر (الـ Dockerfile يسويها تلقائيًا)
    logger.info("التطبيق بدأ التشغيل (%s)", settings.ENVIRONMENT)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan,
    docs_url=None if settings.ENVIRONMENT == "production" else "/docs",
    redoc_url=None if settings.ENVIRONMENT == "production" else "/redoc",
    openapi_url=None if settings.ENVIRONMENT == "production" else "/openapi.json",
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(AuthRateLimitMiddleware)

try:
    from prometheus_fastapi_instrumentator import Instrumentator

    instrumentator = Instrumentator().instrument(app)
    if settings.ENVIRONMENT != "production":
        instrumentator.expose(app, tags=["Monitoring"])
except ImportError:
    logger.info("مكتبة prometheus-fastapi-instrumentator غير مثبّتة — /metrics معطّل")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    if settings.ENVIRONMENT == "production":
        # فقط بالإنتاج (خلف HTTPS) — بالتطوير المحلي (HTTP) تكسر المتصفح لو فعّلناها
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """يمسك أي خطأ غير متوقع (مو HTTPException) — يسجّله ويرجّع رد نظيف بدون تفاصيل داخلية"""
    logger.exception("خطأ غير متوقع في %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "حدث خطأ غير متوقع في الخادم"},
    )


@app.get("/health", tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        logger.exception("فحص الصحة: قاعدة البيانات غير متاحة")
        db_status = "error"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "database": db_status,
        "environment": settings.ENVIRONMENT,
        "app": settings.APP_NAME,
    }


app.include_router(auth_router)
app.include_router(two_factor_router)
app.include_router(users_router)
app.include_router(chat_router)
app.include_router(conversations_router)
app.include_router(files_router)
app.include_router(billing_router)
app.include_router(notifications_router)
app.include_router(admin_router)
