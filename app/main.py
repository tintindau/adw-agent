from fastapi import FastAPI

from app.api.sellout import router as sellout_router
from app.api.sellout_prod_top_class_cat import router as sellout_top_router
from app.api.sellin import router as sellin_router
#from app.api.customer import router as customer_router
from app.api.health import router as health_router

app = FastAPI(
    title="NAW Agent API"
)

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