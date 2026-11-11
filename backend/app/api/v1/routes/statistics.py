from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import Alerts, get_current_user
from app.core.datetime_utils import get_current_time
from app.schemas.alerts import TimelineResponse
from app.schemas.filters import TimeFrame, TimelineParams

router = APIRouter(dependencies=[Depends(get_current_user, scope="function")])

# Window used when the request gives no start date.
DEFAULT_RANGES = {
    TimeFrame.MINUTE: timedelta(hours=1),
    TimeFrame.HOUR: timedelta(days=1),
    TimeFrame.DAY: timedelta(days=30),
    TimeFrame.WEEK: timedelta(days=90),
}

# The series has a bucket for every interval of the window, so the window
# must not be many times longer than the interval is short.
BUCKET_SPAN = {
    TimeFrame.MINUTE: timedelta(minutes=1),
    TimeFrame.HOUR: timedelta(hours=1),
    TimeFrame.DAY: timedelta(days=1),
    TimeFrame.WEEK: timedelta(weeks=1),
}
MAX_BUCKETS = 2000


@router.get("/timeline")
async def get_timeline(
    repo: Alerts, params: Annotated[TimelineParams, Query()]
) -> TimelineResponse:
    """Alert counts per time bucket; every bucket of the window is present, empty ones with 0."""
    end = params.end_date or get_current_time()
    start = params.start_date or end - DEFAULT_RANGES[params.time_frame]
    if (end - start) / BUCKET_SPAN[params.time_frame] > MAX_BUCKETS:
        raise HTTPException(
            status_code=422,
            detail=f"Window too long for {params.time_frame.value} buckets (max {MAX_BUCKETS})",
        )
    window = params.model_copy(update={"start_date": start, "end_date": end})
    data, baseline = await repo.timeline(window, params.time_frame)
    return TimelineResponse(
        time_frame=params.time_frame.value,
        start_date=start,
        end_date=end,
        data=data,
        baseline=baseline,
    )
