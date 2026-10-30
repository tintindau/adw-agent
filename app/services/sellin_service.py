from app.repositories.sellin_repository import RevenueRepository


class RevenueService:

    @staticmethod
    def sales_by_customer(period):

        return RevenueRepository.sales_by_customer(
            period
        )