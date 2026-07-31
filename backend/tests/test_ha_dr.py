import sys
import os
from unittest.mock import patch, MagicMock
import pytest

from core.config import Settings

# Add deploy/scripts to sys.path so we can import dr_failover module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../deploy/scripts")))
import dr_failover


def test_ha_config_settings_and_url_properties():
    settings = Settings(
        HA_MODE_ENABLED=False,
        PROMETHEUS_URL="http://prometheus:9090",
        THANOS_QUERIER_URL="http://thanos-querier:10902",
        PGBOUNCER_HOST="pgbouncer-node",
        PGBOUNCER_PORT=6432,
        PGBOUNCER_USER="ha_admin",
        PGBOUNCER_PASSWORD="ha_password",
        PGBOUNCER_DB="ha_db",
    )

    # When HA_MODE_ENABLED is False, effective_prometheus_url returns PROMETHEUS_URL
    assert settings.effective_prometheus_url == "http://prometheus:9090"
    assert settings.pgbouncer_async_database_url == "postgresql+asyncpg://ha_admin:ha_password@pgbouncer-node:6432/ha_db"

    # When HA_MODE_ENABLED is True, effective_prometheus_url returns THANOS_QUERIER_URL
    ha_settings = Settings(
        HA_MODE_ENABLED=True,
        PROMETHEUS_URL="http://prometheus:9090",
        THANOS_QUERIER_URL="http://thanos-querier:10902",
    )
    assert ha_settings.effective_prometheus_url == "http://thanos-querier:10902"


def test_dr_failover_health_probing():
    with patch("urllib.request.urlopen") as mock_urlopen, \
         patch("subprocess.run") as mock_run:

        # Mock Thanos health check response (200 OK)
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        # Mock pg_isready output
        mock_run_res = MagicMock()
        mock_run_res.returncode = 0
        mock_run.return_value = mock_run_res

        status = dr_failover.check_node_health(
            primary_host="127.0.0.1", primary_port=5432,
            replica_host="127.0.0.1", replica_port=5433,
            pgbouncer_host="127.0.0.1", pgbouncer_port=6432,
            thanos_url="http://localhost:10902"
        )

        assert status["thanos_querier"]["status"] == "HEALTHY"
        assert status["postgres_primary"]["status"] == "HEALTHY"
        assert status["postgres_replica"]["status"] == "HEALTHY"
        assert status["pgbouncer"]["status"] == "HEALTHY"


def test_dr_failover_promotion_logic():
    with patch("subprocess.run") as mock_run:
        mock_res = MagicMock()
        mock_res.stdout = "server promoted"
        mock_res.returncode = 0
        mock_run.return_value = mock_res

        success = dr_failover.promote_replica_to_primary(
            replica_container="test_replica",
            pgbouncer_container="test_pgbouncer"
        )

        assert success is True
        assert mock_run.call_count == 2
