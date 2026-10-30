from datetime import date, datetime, timedelta

from fastapi import APIRouter, HTTPException, Query

from app.services.sellout_service import SelloutService

router = APIRouter()


@router.get("/sellout")
def get_sellout(
    start_date: str | None = Query(
        default=None,
        pattern=r"^\d{8}$",
        description="Inclusive start date in YYYYMMDD format",
    ),
    end_date: str | None = Query(
        default=None,
        pattern=r"^\d{8}$",
        description="Exclusive end date in YYYYMMDD format",
    ),
):
    def parse_date(value: str | None, parameter_name: str) -> date | None:
        if value is None:
            return None
        try:
            return datetime.strptime(value, "%Y%m%d").date()
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail=f"{parameter_name} must be a valid date in YYYYMMDD format",
            ) from exc

    parsed_start = parse_date(start_date, "start_date")
    parsed_end = parse_date(end_date, "end_date")
    resolved_end = parsed_end or date.today() + timedelta(days=1)
    resolved_start = parsed_start or resolved_end - timedelta(days=31)
    if resolved_start >= resolved_end:
        raise HTTPException(
            status_code=422,
            detail="start_date must be earlier than the exclusive end_date",
        )

    return {
        "success": True,
        "data": SelloutService.get_sellout(
            resolved_start.strftime("%Y%m%d"),
            resolved_end.strftime("%Y%m%d"),
        ),
    }