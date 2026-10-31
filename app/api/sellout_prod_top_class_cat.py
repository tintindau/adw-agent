from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query

from app.services.sellout_prod_top_class_cat_service import (
    MAX_LIMIT,
    SelloutProdTopClassCatService,
)

router = APIRouter()


@router.get("/sellout/top-products")
def get_sellout_top_products(
    month: int = Query(..., description="Required month in YYYYMM format"),
    dimensions: Annotated[list[str] | None, Query()] = None,
    rank_type: Literal["top", "bad"] = "top",
    limit: int = Query(20, ge=1, le=MAX_LIMIT),
    prod_code: str | None = None,
    prod_name: str | None = None,
    date_: str | None = None,
    prod_id_kgr: str | None = None,
    prod_name_kgr: str | None = None,
    category_bod: str | None = None,
    is_shibu: int | None = None,
):
    if month % 100 not in range(1, 13):
        raise HTTPException(
            status_code=422,
            detail="month must be in YYYYMM format with a valid month",
        )

    return {
        "success": True,
        "data": SelloutProdTopClassCatService.get_top_products(
            month=month,
            dimensions=dimensions,
            rank_type=rank_type,
            limit=limit,
            prod_code=prod_code,
            prod_name=prod_name,
            date_=date_,
            prod_id_kgr=prod_id_kgr,
            prod_name_kgr=prod_name_kgr,
            category_bod=category_bod,
            is_shibu=is_shibu,
        ),
    }
