from prometheus_client import Counter, Histogram
from prometheus_client.utils import INF

DURATION_BUCKETS = [
    0.05,
    0.1,
    0.2,
    0.25,
    0.5,
    0.75,
    1.0,
    1.5,
    2.0,
    2.5,
    3.0,
    3.5,
    4.0,
    4.5,
    5.0,
    6.0,
    7.5,
    10.0,
    12.5,
    15.0,
    17.5,
    20.0,
    22.5,
    25.0,
    27.5,
    30.0,
    INF,
]


GS_GET_REQUESTS_TOTAL = Counter("boogiestats_gs_get_requests_total", "Number of GS GET requests")
GS_GET_REQUESTS_ERRORS_TOTAL = Counter(
    "boogiestats_gs_get_requests_errors_total", "Number of unsuccessful GS GET requests"
)
GS_GET_REQUEST_DURATION = Histogram(
    "boogiestats_gs_get_request_duration_seconds",
    "Time it took to perform GS GET request",
    buckets=DURATION_BUCKETS,
)

GS_POST_REQUESTS_TOTAL = Counter("boogiestats_gs_post_requests_total", "Number of GS POST requests")
GS_POST_REQUESTS_ERRORS_TOTAL = Counter(
    "boogiestats_gs_post_requests_errors_total", "Number of unsuccessful GS POST requests"
)
GS_POST_REQUEST_DURATION = Histogram(
    "boogiestats_gs_post_request_duration_seconds",
    "Time it took to perform GS POST request",
    buckets=DURATION_BUCKETS,
)

GS_FREED_SCORES = Counter("boogiestats_gs_freed_scores_total", "Number of scores that have skipped GS submit")

BS_SCORE_HANDLING_DURATION = Histogram(
    "boogiestats_score_handling_duration_seconds",
    "Time it took to perform BS part of score handling",
    buckets=DURATION_BUCKETS,
)

SCORE_CREATION_ATTEMPTS = Counter(
    "boogiestats_score_creation_attempts_total",
    "Number of attempts to create a score",
    labelnames=["attempt"],
)
SCORES_CREATED = Counter("boogiestats_scores_created_total", "Number of scores created")
