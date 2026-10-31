from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query

from app.services.sellout_service import SelloutService

router = APIRouter()


@router.get("/sellout")
def get_sellout(
    month: int = Query(..., description="Required month in YYYYMM format"),
    dimensions: Annotated[list[str] | None, Query()] = None,
    metrics: Annotated[list[str] | None, Query()] = None,
    date_: str | None = None,
    region: str | None = None,
    province: str | None = None,
    prod_class_dmx: str | None = None,
    prod_category: str | None = None,
    is_shibu: int | None = None,
    is_dummy: int | None = None,
    prod_type: Literal["Shibu", "Trung_bay", "Con_lai"] | None = None,
    gh_flow: str | None = None,
):
    if month % 100 not in range(1, 13):
        raise HTTPException(
            status_code=422,
            detail="month must be in YYYYMM format with a valid month",
        )

    return {
        "success": True,
        "data": SelloutService.get_aggregated_siso(
            month=month,
            dimensions=dimensions,
            metrics=metrics,
            date_=date_,
            region=region,
            province=province,
            prod_class_dmx=prod_class_dmx,
            prod_category=prod_category,
            is_shibu=is_shibu,
            is_dummy=is_dummy,
            prod_type=prod_type,
            gh_flow=gh_flow,
        ),
    }