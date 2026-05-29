from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

ASK_REQUESTS = Counter("llm_monitor_ask_requests_total", "Total /ask requests", ["relay"])
HIGH_RISK_RESPONSES = Counter("llm_monitor_high_risk_total", "Total high-risk responses")
ANALYSIS_LATENCY = Histogram("llm_monitor_analysis_latency_seconds", "Analysis latency in seconds")
DRIFT_SCORE = Gauge("llm_monitor_latest_drift_score", "Latest drift score")
ACTIVE_WEBSOCKETS = Gauge("llm_monitor_active_websockets", "Active WebSocket clients")
RISK_SCORE = Gauge("llm_monitor_latest_risk_score", "Latest risk score")


def metrics_response() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
