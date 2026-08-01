import time
import uuid

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from models.node import Node
from schemas.metrics import MetricDataPoint, MetricSeriesResponse

ALLOWED_METRICS = {
    "cpu_usage": 'infra_cpu_usage_ratio{{node_id="{node_id}"}} * 100',
    "ram_usage": 'infra_ram_usage_percent{{node_id="{node_id}"}}',
    "disk_usage": 'infra_disk_usage_percent{{node_id="{node_id}"}}',
    "network_in": 'rate(infra_network_bytes_received_total{{node_id="{node_id}"}}[5m])',
    "network_out": 'rate(infra_network_bytes_transmitted_total{{node_id="{node_id}"}}[5m])',
}

# (duration_seconds, step_seconds)
ALLOWED_RANGES = {
    "1h": (3600, 60),
    "6h": (21600, 300),
    "24h": (86400, 900),
    "7d": (604800, 3600),
    "30d": (2592000, 14400),
}


async def query_node_metrics(
    db: AsyncSession,
    node_id: uuid.UUID,
    metric_name: str = "cpu_usage",
    range_str: str = "1h",
    client: httpx.AsyncClient | None = None,
) -> MetricSeriesResponse:
    """
    Backend service for querying node metrics from Prometheus.
    - Validates node_id exists in database.
    - Enforces metric_name allowlist and range_str allowlist.
    - Maps query to bounded time-series.
    """
    # 1. Check Node existence
    node = await db.get(Node, node_id)
    if not node:
        raise KeyError(f"Node '{node_id}' not found.")

    # 2. Validate metric_name
    if metric_name not in ALLOWED_METRICS:
        raise ValueError(
            f"Metric name '{metric_name}' is not allowed. Allowed: {list(ALLOWED_METRICS.keys())}"
        )

    # 3. Validate range_str
    if range_str not in ALLOWED_RANGES:
        raise ValueError(
            f"Range '{range_str}' is not allowed. Allowed: {list(ALLOWED_RANGES.keys())}"
        )

    duration, step = ALLOWED_RANGES[range_str]
    now_ts = time.time()
    start_ts = now_ts - duration
    promql_template = ALLOWED_METRICS[metric_name]
    promql_query = promql_template.format(node_id=str(node_id))

    params = {
        "query": promql_query,
        "start": start_ts,
        "end": now_ts,
        "step": step,
    }

    prometheus_api_url = f"{settings.PROMETHEUS_URL.rstrip('/')}/api/v1/query_range"

    close_client_after = False
    if client is None:
        client = httpx.AsyncClient(timeout=5.0)
        close_client_after = True

    try:
        resp = await client.get(prometheus_api_url, params=params)
        if resp.status_code != 200:
            raise RuntimeError(f"Prometheus returned status {resp.status_code}: {resp.text}")

        data = resp.json()
        if data.get("status") != "success":
            raise RuntimeError(f"Prometheus query error: {data.get('error', 'unknown error')}")

        result_matrix = data.get("data", {}).get("result", [])
        datapoints: list[MetricDataPoint] = []

        if result_matrix:
            raw_values = result_matrix[0].get("values", [])
            for ts, val in raw_values:
                try:
                    datapoints.append(MetricDataPoint(timestamp=float(ts), value=float(val)))
                except (ValueError, TypeError):
                    continue

        return MetricSeriesResponse(
            node_id=node_id,
            metric_name=metric_name,
            range=range_str,
            datapoints=datapoints,
        )

    except httpx.TimeoutException as exc:
        raise TimeoutError("Prometheus query timed out.") from exc
    except httpx.RequestError as exc:
        raise RuntimeError(f"Could not connect to Prometheus: {exc}") from exc
    finally:
        if close_client_after:
            await client.aclose()
