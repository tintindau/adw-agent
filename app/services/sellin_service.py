from app.repositories.sellin_repository import RevenueRepository, SellinRepository


class RevenueService:
    @staticmethod
    def sales_by_customer(period):
        return RevenueRepository.sales_by_customer(period)


class SellinService:
    @staticmethod
    def get_by_month(filters: dict[str, str | None]):
        return SellinRepository.get_by_month(filters)
