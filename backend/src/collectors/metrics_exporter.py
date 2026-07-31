import logging
from typing import Any

from prometheus_client import CollectorRegistry, Gauge, start_http_server

logger = logging.getLogger(__name__)

# Single custom registry for collector worker metrics
collector_registry = CollectorRegistry()

# Gauges with stable node_id label
CPU_USAGE = Gauge(
    "infra_cpu_usage_ratio",
    "CPU usage ratio (0.0 to 1.0)",
    ["node_id"],
    registry=collector_registry,
)
RAM_USAGE_BYTES = Gauge(
    "infra_ram_usage_bytes",
    "RAM usage in bytes",
    ["node_id"],
    registry=collector_registry,
)
DISK_USAGE_BYTES = Gauge(
    "infra_disk_usage_bytes",
    "Disk usage in bytes",
    ["node_id"],
    registry=collector_registry,
)
NETWORK_IN_BYTES = Gauge(
    "infra_network_bytes_received_total",
    "Total network bytes received",
    ["node_id"],
    registry=collector_registry,
)
NETWORK_OUT_BYTES = Gauge(
    "infra_network_bytes_transmitted_total",
    "Total network bytes transmitted",
    ["node_id"],
    registry=collector_registry,
)
NODE_STATUS = Gauge(
    "infra_node_status",
    "Current status of node (1=UP, 0.5=WARNING, 0=DOWN, -1=UNKNOWN)",
    ["node_id"],
    registry=collector_registry,
)

STATUS_MAP = {
    "up": 1.0,
    "warning": 0.5,
    "down": 0.0,
    "unknown": -1.0,
}


def update_node_metrics(
    node_id: str,
    status: str,
    cpu_usage_ratio: float | None = None,
    ram_usage_bytes: int | None = None,
    disk_usage_bytes: int | None = None,
    network_in_bytes: int | None = None,
    network_out_bytes: int | None = None,
) -> None:
    """
    Update metrics series for a given node_id.
    """
    status_code = STATUS_MAP.get(status.lower(), -1.0)
    NODE_STATUS.labels(node_id=node_id).set(status_code)

    if cpu_usage_ratio is not None:
        CPU_USAGE.labels(node_id=node_id).set(cpu_usage_ratio)
    if ram_usage_bytes is not None:
        RAM_USAGE_BYTES.labels(node_id=node_id).set(ram_usage_bytes)
    if disk_usage_bytes is not None:
        DISK_USAGE_BYTES.labels(node_id=node_id).set(disk_usage_bytes)
    if network_in_bytes is not None:
        NETWORK_IN_BYTES.labels(node_id=node_id).set(network_in_bytes)
    if network_out_bytes is not None:
        NETWORK_OUT_BYTES.labels(node_id=node_id).set(network_out_bytes)


def remove_node_metrics(node_id: str) -> None:
    """
    Stale-series cleanup: remove all metric labels for a deleted or archived node.
    """
    for gauge in (
        CPU_USAGE,
        RAM_USAGE_BYTES,
        DISK_USAGE_BYTES,
        NETWORK_IN_BYTES,
        NETWORK_OUT_BYTES,
        NODE_STATUS,
    ):
        try:
            gauge.remove(node_id)
        except KeyError:
            pass


def start_worker_metrics_server(port: int = 8001) -> None:
    """
    Start Prometheus HTTP server on specified port exposing collector_registry.
    """
    try:
        start_http_server(port, registry=collector_registry)
        logger.info(f"Worker Prometheus metrics server started on port {port}")
    except Exception as exc:
        logger.warning(f"Could not start Prometheus metrics server on port {port}: {exc}")
