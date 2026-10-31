from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from app.services.sellin_service import RevenueService, SellinService

router = APIRouter()


@router.get("/sales/customer")
def sales_by_customer(
    period:str
):

    return RevenueService.sales_by_customer(
        period
    )


@router.get("/sellin")
def get_sellin_by_month(
    month_: str = Query(..., description="Required month key"),
    date_: str | None = Query(default=None, pattern=r"^\d{8}$"),
    from_date: str | None = Query(default=None, pattern=r"^\d{8}$"),
    to_date: str | None = Query(default=None, pattern=r"^\d{8}$"),
    store_name: str | None = None,
    store_code: str | None = None,
    region: str | None = None,
    province: str | None = None,
    prod_code: str | None = None,
    prod_name: str | None = None,
    model_name: str | None = None,
    prod_class_dmx: str | None = None,
    prod_category: str | None = None,
    is_shibu: str | None = None,
    is_dummy: str | None = None,
):
    dates = {
        "date_": date_,
        "from_date": from_date,
        "to_date": to_date,
    }
    for parameter, value in dates.items():
        if value is not None:
            try:
                datetime.strptime(value, "%Y%m%d")
            except ValueError as exc:
                raise HTTPException(
                    status_code=422,
                    detail=f"{parameter} must be a valid date in YYYYMMDD format",
                ) from exc

    if date_ is not None and (from_date is not None or to_date is not None):
        raise HTTPException(
            status_code=422,
            detail="Use date_ or from_date/to_date, not both",
        )
    if from_date is not None and to_date is not None and from_date > to_date:
        raise HTTPException(
            status_code=422,
            detail="from_date must be earlier than or equal to to_date",
        )

    filters = {
        "month_": month_,
        "date_": date_,
        "from_date": from_date,
        "to_date": to_date,
        "store_name": store_name,
        "store_code": store_code,
        "region": region,
        "province": province,
        "prod_code": prod_code,
        "prod_name": prod_name,
        "model_name": model_name,
        "prod_class_dmx": prod_class_dmx,
        "prod_category": prod_category,
        "is_shibu": is_shibu,
        "is_dummy": is_dummy,
    }
    return {
        "success": True,
        "data": SellinService.get_by_month(filters),
    }