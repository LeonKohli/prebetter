"""Typical alert volume per hour, taken from the same hour of the previous weeks.

Alert counts follow a daily and weekly cycle, so a flat average says little: the
question an analyst has is whether this hour is busier than a comparable hour.
The baseline is the median of the same hour-of-week in the previous weeks. The
band around it uses the median absolute deviation, which a burst in one of the
weeks does not distort the way a standard deviation would.
"""

import math
from datetime import datetime, timedelta
from statistics import median

from app.schemas.alerts import BaselinePoint

WEEKS = 4
# Fewer same-hour samples than this say too little; the hour then has no band.
MIN_SAMPLES = 3
# Band half-width in robust standard deviations (MAD scaled to sigma).
BAND_WIDTH = 2.5
MAD_TO_SIGMA = 1.4826

HOUR = timedelta(hours=1)
WEEK = timedelta(weeks=1)


def band(samples: list[int]) -> tuple[int, int, float] | None:
    """(low, high, typical) for one hour, or None without enough samples.

    Counts are small and Poisson-like, so the spread never drops below the
    square root of the median, and below 1: a quiet hour has a band, not a point.
    """
    if len(samples) < MIN_SAMPLES:
        return None
    typical = median(samples)
    mad = median(abs(sample - typical) for sample in samples)
    spread = max(MAD_TO_SIGMA * mad, math.sqrt(typical), 1.0)
    low = max(0, math.floor(typical - BAND_WIDTH * spread))
    high = math.ceil(typical + BAND_WIDTH * spread)
    return low, high, round(typical, 1)


def seasonal_baseline(
    counts: dict[datetime, int], hours: list[datetime], first_seen: datetime | None
) -> list[BaselinePoint]:
    """Band for each hour that has enough history.

    `counts` holds every hour of the lookback window (empty hours as 0).
    Weeks before the first stored event are skipped, not counted as quiet.
    """
    oldest = first_seen.replace(minute=0, second=0, microsecond=0) if first_seen else None
    points = []
    for hour in hours:
        samples = []
        for weeks_back in range(1, WEEKS + 1):
            earlier = hour - weeks_back * WEEK
            if earlier in counts and (oldest is None or earlier >= oldest):
                samples.append(counts[earlier])
        result = band(samples)
        if result:
            low, high, typical = result
            points.append(
                BaselinePoint(timestamp=hour, low=low, high=high, typical=typical)
            )
    return points
