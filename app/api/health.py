from fastapi import APIRouter

from app.db.query_executor import query_cache

router = APIRouter()


@router.get("/health")
def health():
	return {
		"success": True,
		"data": {"status": "ok", "query_cache": query_cache.stats()},
	}
