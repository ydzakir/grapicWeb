import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from main import app
from models.audit import AuditLog
from models.node import LifecycleStatus, Node, NodeStatus, NodeType, ReviewStatus
from models.user import User, UserRole
from services.datacenter_service import assign_hosts_to_datacenter, create_datacenter
from services.node_service import (
    approve_node,
    archive_node,
    reject_node,
    upsert_inventory_node,
    validate_host_naming_convention,
)
from services.topology_service import build_topology_graph


@pytest.mark.asyncio
async def test_host_naming_convention_validation():
    # Valid naming convention: [TYPE]-[LOKASI]-[FUNGSI]-[NOMOR]
    valid, err = validate_host_naming_convention("HYPERV-DC1-WEB-01")
    assert valid is True
    assert err is None

    valid, err = validate_host_naming_convention("DOCKER-DC2-APP-99")
    assert valid is True

    valid, err = validate_host_naming_convention("PHYSICAL-SG-DB-01")
    assert valid is True

    # Invalid host names
    valid, err = validate_host_naming_convention("invalid-host-name")
    assert valid is False
    assert "convention" in err.lower()

    valid, err = validate_host_naming_convention("SERVER123")
    assert valid is False


@pytest.mark.asyncio
async def test_idempotent_normalized_inventory_upsert(db_session):
    # 1. Upsert a canonical Docker host
    host = await upsert_inventory_node(
        db=db_session,
        name="DOCKER-DC1-APP-01",
        node_type=NodeType.DOCKER_HOST,
        ip_address="192.168.1.50",
        os="Ubuntu 22.04 LTS",
        cpu_cores=8,
        ram_mb=16384,
        disk_gb=250.0,
        status=NodeStatus.UP,
        metadata={"machine_id": "mach-001"},
    )
    await db_session.commit()

    assert host.id is not None
    assert host.review_status == ReviewStatus.PENDING
    assert host.status == NodeStatus.UP

    # 2. Re-run scan with updated metrics on the same host (same IP / machine_id)
    host_rescan = await upsert_inventory_node(
        db=db_session,
        name="DOCKER-DC1-APP-01",
        node_type=NodeType.DOCKER_HOST,
        ip_address="192.168.1.50",
        os="Ubuntu 22.04 LTS",
        cpu_cores=8,
        ram_mb=16384,
        disk_gb=300.0,  # updated disk
        status=NodeStatus.UP,
        metadata={"machine_id": "mach-001"},
    )
    await db_session.commit()

    assert host_rescan.id == host.id
    assert host_rescan.disk_gb == 300.0

    # Count nodes in DB -> should only be 1 host
    stmt = select(Node).where(Node.type == NodeType.DOCKER_HOST)
    res = await db_session.execute(stmt)
    assert len(list(res.scalars().all())) == 1


@pytest.mark.asyncio
async def test_container_naming_and_parent_inference(db_session):
    # Create Docker Host
    host = await upsert_inventory_node(
        db=db_session,
        name="DOCKER-DC1-WEB-01",
        node_type=NodeType.DOCKER_HOST,
        ip_address="10.0.0.10",
    )
    await db_session.commit()

    # Upsert container under host
    container = await upsert_inventory_node(
        db=db_session,
        name="/nginx-frontend",
        node_type=NodeType.DOCKER_CONTAINER,
        parent_id=host.id,
        status=NodeStatus.UP,
    )
    await db_session.commit()

    assert container.name == "DOCKER-DC1-WEB-01/nginx-frontend"
    assert container.parent_id == host.id
    assert container.metadata_["container_name"] == "/nginx-frontend"

    # Rescan container
    container_rescan = await upsert_inventory_node(
        db=db_session,
        name="/nginx-frontend",
        node_type=NodeType.DOCKER_CONTAINER,
        parent_id=host.id,
        status=NodeStatus.UP,
    )
    await db_session.commit()

    assert container_rescan.id == container.id

    stmt = select(Node).where(Node.type == NodeType.DOCKER_CONTAINER)
    res = await db_session.execute(stmt)
    assert len(list(res.scalars().all())) == 1


@pytest.mark.asyncio
async def test_invalid_name_discovery_and_approval_enforcement(db_session):
    # Create an admin user for approval actions
    admin = User(
        username="admin_approver",
        email="admin_app@example.com",
        hashed_password="hash",
        role=UserRole.ADMIN,
    )
    db_session.add(admin)
    await db_session.flush()

    # Discovery with invalid naming convention
    invalid_host = await upsert_inventory_node(
        db=db_session,
        name="bad_host_name_123",
        node_type=NodeType.HYPERV_HOST,
        ip_address="10.0.0.20",
    )
    await db_session.commit()

    assert invalid_host.review_status == ReviewStatus.PENDING
    assert "validation_issue" in invalid_host.metadata_

    # Attempt to approve without providing valid name -> throws ValueError
    with pytest.raises(ValueError) as exc:
        await approve_node(db=db_session, node_id=invalid_host.id, admin_user=admin)
    assert "convention" in str(exc.value)

    # Approve with corrected valid name
    approved_host = await approve_node(
        db=db_session,
        node_id=invalid_host.id,
        admin_user=admin,
        new_name="HYPERV-DC1-HOST-01",
    )
    await db_session.commit()

    assert approved_host.name == "HYPERV-DC1-HOST-01"
    assert approved_host.review_status == ReviewStatus.APPROVED
    assert "validation_issue" not in approved_host.metadata_


@pytest.mark.asyncio
async def test_datacenter_grouping_and_host_assignment(db_session):
    admin = User(
        username="dc_admin",
        email="dcadmin@example.com",
        hashed_password="hash",
        role=UserRole.ADMIN,
    )
    db_session.add(admin)
    await db_session.flush()

    dc = await create_datacenter(
        db=db_session,
        name="Data Center Jakarta",
        location="JKT-01",
        admin_user=admin,
    )
    await db_session.commit()

    assert dc.type == NodeType.DATA_CENTER
    assert dc.review_status == ReviewStatus.APPROVED

    host = await upsert_inventory_node(
        db=db_session,
        name="HYPERV-JKT-APP-01",
        node_type=NodeType.HYPERV_HOST,
    )
    await db_session.commit()

    assigned = await assign_hosts_to_datacenter(
        db=db_session,
        datacenter_id=dc.id,
        host_ids=[host.id],
        admin_user=admin,
    )
    await db_session.commit()

    assert assigned[0].parent_id == dc.id


@pytest.mark.asyncio
async def test_topology_builder_engine_and_cycle_defense(db_session):
    admin = User(
        username="topo_admin",
        email="topoadmin@example.com",
        hashed_password="hash",
        role=UserRole.ADMIN,
    )
    db_session.add(admin)
    await db_session.flush()

    # Create approved hierarchy: DC -> Host -> VM -> Container
    dc = await create_datacenter(db=db_session, name="DC Main", admin_user=admin)

    host = await upsert_inventory_node(
        db=db_session,
        name="HYPERV-DC1-SRV-01",
        node_type=NodeType.HYPERV_HOST,
        parent_id=dc.id,
    )
    await approve_node(db=db_session, node_id=host.id, admin_user=admin)

    vm = await upsert_inventory_node(
        db=db_session,
        name="VM-WEB-01",
        node_type=NodeType.HYPERV_VM,
        parent_id=host.id,
    )
    await approve_node(db=db_session, node_id=vm.id, admin_user=admin)

    # Add a pending container
    pending_container = await upsert_inventory_node(
        db=db_session,
        name="/pending-app",
        node_type=NodeType.DOCKER_CONTAINER,
        parent_id=host.id,
    )
    await db_session.commit()

    # Default topology graph (approved only)
    graph_default = await build_topology_graph(db=db_session, include_pending=False)
    node_ids_default = {n.id for n in graph_default.nodes}

    assert dc.id in node_ids_default
    assert host.id in node_ids_default
    assert vm.id in node_ids_default
    assert pending_container.id not in node_ids_default  # pending node hidden by default

    # Topology graph including pending
    graph_all = await build_topology_graph(db=db_session, include_pending=True)
    node_ids_all = {n.id for n in graph_all.nodes}
    assert pending_container.id in node_ids_all

    # Verify edge presence
    edge_sources = {e.source for e in graph_default.edges}
    edge_targets = {e.target for e in graph_default.edges}
    assert str(dc.id) in edge_sources
    assert str(host.id) in edge_targets


@pytest.mark.asyncio
async def test_archive_lifecycle_retention(db_session):
    admin = User(
        username="archiver",
        email="archiver@example.com",
        hashed_password="hash",
        role=UserRole.ADMIN,
    )
    db_session.add(admin)
    await db_session.flush()

    host = await upsert_inventory_node(
        db=db_session,
        name="PHYSICAL-DC1-OLD-01",
        node_type=NodeType.PHYSICAL_SERVER,
    )
    await db_session.commit()

    archived = await archive_node(db=db_session, node_id=host.id, admin_user=admin)
    await db_session.commit()

    assert archived.lifecycle_status == LifecycleStatus.ARCHIVED

    # Node still exists in DB (not hard-deleted)
    node_db = await db_session.get(Node, host.id)
    assert node_db is not None
    assert node_db.lifecycle_status == LifecycleStatus.ARCHIVED


# ==================== API ENDPOINT TESTS ==================== #

@pytest.mark.asyncio
async def test_api_nodes_list_pagination_and_filters(db_session):
    # Create test user & tokens
    admin = User(
        username="api_admin",
        email="api_admin@example.com",
        hashed_password="hash",
        role=UserRole.ADMIN,
    )
    db_session.add(admin)
    await db_session.flush()

    # Create 3 nodes
    n1 = await upsert_inventory_node(
        db=db_session, name="PHYSICAL-DC1-WEB-01", node_type=NodeType.PHYSICAL_SERVER
    )
    n2 = await upsert_inventory_node(
        db=db_session, name="DOCKER-DC1-APP-02", node_type=NodeType.DOCKER_HOST
    )
    n3 = await upsert_inventory_node(
        db=db_session, name="HYPERV-DC2-DB-03", node_type=NodeType.HYPERV_HOST
    )
    await db_session.commit()

    from core.security import create_access_token
    token = create_access_token(subject=str(admin.id), role=admin.role.value)
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # List nodes paginated
        resp = await client.get("/api/v1/nodes?page=1&page_size=2", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 3
        assert len(body["items"]) == 2

        # Search filter
        resp = await client.get("/api/v1/nodes?search=DOCKER", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["name"] == "DOCKER-DC1-APP-02"


@pytest.mark.asyncio
async def test_api_node_approval_and_rbac(db_session):
    admin = User(
        username="rbac_admin",
        email="admin@example.com",
        hashed_password="hash",
        role=UserRole.ADMIN,
    )
    operator = User(
        username="rbac_operator",
        email="operator@example.com",
        hashed_password="hash",
        role=UserRole.OPERATOR,
    )
    db_session.add_all([admin, operator])
    await db_session.flush()

    node = await upsert_inventory_node(
        db=db_session, name="HYPERV-DC1-TEST-01", node_type=NodeType.HYPERV_HOST
    )
    await db_session.commit()

    from core.security import create_access_token
    admin_token = create_access_token(subject=str(admin.id), role=admin.role.value)
    operator_token = create_access_token(subject=str(operator.id), role=operator.role.value)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Operator tries to approve -> 403 Forbidden
        resp = await client.post(
            f"/api/v1/nodes/{node.id}/approve",
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        assert resp.status_code == 403

        # Admin approves -> 200 OK
        resp = await client.post(
            f"/api/v1/nodes/{node.id}/approve",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["review_status"] == "approved"


@pytest.mark.asyncio
async def test_api_topology_endpoint(db_session):
    admin = User(
        username="topo_user",
        email="topo@example.com",
        hashed_password="hash",
        role=UserRole.ADMIN,
    )
    db_session.add(admin)
    await db_session.flush()

    from core.security import create_access_token
    token = create_access_token(subject=str(admin.id), role=admin.role.value)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/v1/topology", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "nodes" in body
        assert "edges" in body
