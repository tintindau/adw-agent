from fastapi import FastAPI

from app.core.audit_middleware import register_audit_middleware
from app.core.config import settings
from app.core.logger import setup_logging

from app.api.sellout import router as sellout_router
from app.api.sellout_prod_top_class_cat import router as sellout_top_router
from app.api.sellin import router as sellin_router
#from app.api.customer import router as customer_router
from app.api.health import router as health_router

setup_logging(
    level=settings.log_level,
    log_dir=settings.log_dir or None,
    json_format=settings.log_json,
    timezone_name=settings.log_timezone,
    retention_days=settings.log_retention_days,
)

app = FastAPI(
    title="NAW Agent API"
)
register_audit_middleware(app)

app.include_router(
    health_router,
    prefix="/api"
)

app.include_router(
    sellin_router,
    prefix="/api"
)

app.include_router(
    sellout_router,
    prefix="/api"
)

app.include_router(
    sellout_top_router,
    prefix="/api"
)

#app.include_router(
#    customer_router,
#    prefix="/api"
#)