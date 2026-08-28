from fastapi import FastAPI
from prometheus_client import Counter, Gauge
from prometheus_fastapi_instrumentator import Instrumentator

TASK_MUTATION_COUNTER = Counter(
    "saas_task_mutations_total",
    "Total number of task mutations created or updated",
    ["action", "priority"],
)

ACTIVE_WS_CONNECTIONS = Gauge(
    "saas_active_websocket_connections",
    "Current active real-time WebSocket connections",
)

STORAGE_OPERATIONS_TOTAL = Counter(
    "saas_storage_operations_total",
    "Total presigned S3 storage operations requested",
    ["operation_type"],
)


def setup_telemetry(app: FastAPI) -> Instrumentator:
    """Configures Prometheus telemetry instrumentation and registers default HTTP metrics."""
    instrumentator = Instrumentator(
        should_group_status_codes=False,
        should_ignore_untemplated=True,
        should_respect_env_var=False,  # Always expose in all environments
        excluded_handlers=["/metrics", "/healthz", "/readyz"],
    )
    instrumentator.instrument(app)
    return instrumentator
