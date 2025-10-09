from fastapi import APIRouter, Query

router = APIRouter(prefix="/metrics", tags=["metrics"])

@router.get("/latest", include_in_schema=True)
def metrics_latest(athlete_id: int = Query(..., ge=1)):
    # TODO: replace with real DB fetch
    return {"athlete_id": athlete_id, "ok": True}
