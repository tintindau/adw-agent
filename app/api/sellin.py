from fastapi import APIRouter

from app.services.sellin_service import RevenueService

router = APIRouter()


@router.get("/sales/customer")
def sales_by_customer(
    period:str
):

    return RevenueService.sales_by_customer(
        period
    )