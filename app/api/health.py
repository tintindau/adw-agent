from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health():
	return {
		"success": True,
		"data": {"status": "ok"},
	}
