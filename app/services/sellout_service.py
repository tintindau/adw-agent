from app.repositories.sellout_repository import SelloutRepository


class SelloutService:
	@staticmethod
	def get_sellout(start_date: str, end_date: str):
		return SelloutRepository.get_sellout(start_date, end_date)
