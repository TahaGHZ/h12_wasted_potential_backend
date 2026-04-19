from fastapi import APIRouter

from backend.services.air_quality.service import get_air_quality_summary

router = APIRouter()


@router.get("/air-quality/summary")
def air_quality_summary():
    return get_air_quality_summary(hours_ahead=168, step_hours=6)
