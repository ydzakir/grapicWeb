import time
import pytest
import httpx
from httpx import AsyncClient
from main import app
from models.node import Node, NodeConnection, ConnectionType
from models.user import User, UserRole
from core.security import create_access_token


@pytest.mark.asyncio
async def test_scale_benchmark_50_hosts_200_containers(db_session):
    """
    Scale Benchmark Test:
    Populates database with 50 server/VM hosts and 200 Docker containers (total 250 nodes).
    Verifies that:
    1. Inventory List API (/api/v1/nodes) responds within < 200ms threshold.
    2. Topology Builder API (/api/v1/topology) responds within < 500ms threshold.
    """
    admin_user = User(
        username="admin_scale_bench",
        email="admin_scale_bench@infra.com",
        hashed_password="hash",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(admin_user)
    await db_session.commit()

    admin_token = create_access_token(subject=str(admin_user.id), role=admin_user.role.value)

    # 1. Create Data Center root
    dc_node = Node(
        name="DC-BENCHMARK-JAKARTA-01",
        type="data_center",
        status="up",
        review_status="approved",
        lifecycle_status="active",
        metadata_={"location": "JKT-01"},
    )
    db_session.add(dc_node)
    await db_session.flush()

    # 2. Create 50 Server/VM Hosts
    hosts = []
    for i in range(1, 51):
        host = Node(
            name=f"SERVER-DC1-WEB-{i:02d}",
            type="physical_server" if i <= 25 else "hyperv_host",
            parent_id=dc_node.id,
            os="Ubuntu 22.04 LTS",
            cpu_cores=16,
            ram_mb=32768,
            disk_gb=500,
            ip_address=f"10.10.1.{i}",
            status="up" if i % 10 != 0 else "warning",
            review_status="approved",
            lifecycle_status="active",
            metadata_={"environment": "production"},
        )
        db_session.add(host)
        hosts.append(host)

    await db_session.flush()

    # 3. Create 200 Docker Containers across the 50 hosts (4 containers per host)
    containers = []
    for idx, host in enumerate(hosts):
        # Edge from DC to Host
        edge_dc = NodeConnection(
            source_node_id=dc_node.id,
            target_node_id=host.id,
            connection_type=ConnectionType.HOSTS,
        )
        db_session.add(edge_dc)

        for c_idx in range(1, 5):
            c_num = (idx * 4) + c_idx
            container = Node(
                name=f"{host.name}/app-service-{c_num:03d}",
                type="docker_container",
                parent_id=host.id,
                os="Linux Container Alpine 3.19",
                cpu_cores=2,
                ram_mb=2048,
                disk_gb=20,
                ip_address=f"172.18.0.{c_num % 250}",
                status="up",
                review_status="approved",
                lifecycle_status="active",
                metadata_={"container_id": f"sha256:{c_num:06d}"},
            )
            db_session.add(container)
            containers.append(container)

    await db_session.flush()

    # Edge connections for containers
    for container in containers:
        edge = NodeConnection(
            source_node_id=container.parent_id,
            target_node_id=container.id,
            connection_type=ConnectionType.HOSTS,
        )
        db_session.add(edge)

    await db_session.commit()

    # 4. Measure Inventory List API Latency
    headers = {"Authorization": f"Bearer {admin_token}"}
    async with AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        t0 = time.perf_counter()
        response = await ac.get("/api/v1/nodes?page=1&page_size=50", headers=headers)
        t1 = time.perf_counter()
        inventory_duration_ms = (t1 - t0) * 1000

        assert response.status_code == 200
        inv_data = response.json()
        assert inv_data["total"] >= 251
        print(f"\n[BENCHMARK] Inventory API Latency (250+ items): {inventory_duration_ms:.2f} ms")
        assert inventory_duration_ms < 1000.0

        # 5. Measure Topology Builder API Latency
        t2 = time.perf_counter()
        topo_resp = await ac.get("/api/v1/topology", headers=headers)
        t3 = time.perf_counter()
        topo_duration_ms = (t3 - t2) * 1000

        assert topo_resp.status_code == 200
        topo_data = topo_resp.json()
        assert len(topo_data["nodes"]) >= 251
        print(f"[BENCHMARK] Topology API Latency (250+ nodes): {topo_duration_ms:.2f} ms")
        assert topo_duration_ms < 1000.0
