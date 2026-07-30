import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from models.collector import CollectorRun, CollectorRunStatus, CollectorTarget, TargetType
from models.node import (
    ConnectionType,
    Node,
    NodeConnection,
    NodeStatus,
    NodeType,
    ReviewStatus,
)
from models.user import User, UserRole


@pytest.mark.asyncio
async def test_create_user_model(db_session: AsyncSession):
    user = User(
        username="testoperator",
        email="operator@infra.com",
        hashed_password="dummy_hashed_password",
        role=UserRole.OPERATOR,
    )
    db_session.add(user)
    await db_session.flush()

    assert user.id is not None
    assert user.username == "testoperator"
    assert user.role == UserRole.OPERATOR
    assert user.is_active is True


@pytest.mark.asyncio
async def test_unique_user_constraints(db_session: AsyncSession):
    u1 = User(
        username="duplicate_user",
        email="dup@infra.com",
        hashed_password="pass",
        role=UserRole.VIEWER,
    )
    db_session.add(u1)
    await db_session.flush()

    u2 = User(
        username="duplicate_user",
        email="other@infra.com",
        hashed_password="pass",
        role=UserRole.VIEWER,
    )
    db_session.add(u2)

    with pytest.raises(IntegrityError):
        await db_session.flush()

    await db_session.rollback()


@pytest.mark.asyncio
async def test_node_and_connection_models(db_session: AsyncSession):
    dc = Node(
        name="DC1-JKT",
        type=NodeType.DATA_CENTER,
        status=NodeStatus.UP,
        review_status=ReviewStatus.APPROVED,
    )
    db_session.add(dc)
    await db_session.flush()

    host = Node(
        name="HV-DC1-WEB-01",
        type=NodeType.HYPERVISOR_HOST,
        parent_id=dc.id,
        status=NodeStatus.UP,
        review_status=ReviewStatus.APPROVED,
        os="Windows Server 2022",
        cpu_cores=32,
        ram_mb=131072,
        disk_gb=2000.0,
    )
    db_session.add(host)
    await db_session.flush()

    vm = Node(
        name="VM-DC1-WEB-01",
        type=NodeType.VM,
        parent_id=host.id,
        status=NodeStatus.UP,
        review_status=ReviewStatus.APPROVED,
    )
    db_session.add(vm)
    await db_session.flush()

    # Edge connection
    conn = NodeConnection(
        source_node_id=host.id,
        target_node_id=vm.id,
        connection_type=ConnectionType.HOSTS,
    )
    db_session.add(conn)
    await db_session.flush()

    assert vm.parent_id == host.id
    assert conn.id is not None


@pytest.mark.asyncio
async def test_edge_deduplication_constraint(db_session: AsyncSession):
    n1 = Node(name="NodeA", type=NodeType.PHYSICAL_SERVER)
    n2 = Node(name="NodeB", type=NodeType.PHYSICAL_SERVER)
    db_session.add_all([n1, n2])
    await db_session.flush()

    conn1 = NodeConnection(
        source_node_id=n1.id,
        target_node_id=n2.id,
        connection_type=ConnectionType.NETWORK,
    )
    db_session.add(conn1)
    await db_session.flush()

    # Duplicate connection with same source, target, type
    conn2 = NodeConnection(
        source_node_id=n1.id,
        target_node_id=n2.id,
        connection_type=ConnectionType.NETWORK,
    )
    db_session.add(conn2)

    with pytest.raises(IntegrityError):
        await db_session.flush()

    await db_session.rollback()


@pytest.mark.asyncio
async def test_collector_target_and_run_models(db_session: AsyncSession):
    target = CollectorTarget(
        name="Linux Web Cluster 01",
        target_type=TargetType.SSH,
        host="192.168.1.10",
        port=22,
        credential_reference="docker_secret:ssh_web_key",
    )
    db_session.add(target)
    await db_session.flush()

    run = CollectorRun(
        target_id=target.id,
        status=CollectorRunStatus.SUCCESS,
        last_attempt_at=target.created_at,
    )
    db_session.add(run)
    await db_session.flush()

    assert target.credential_reference == "docker_secret:ssh_web_key"
    assert run.target_id == target.id
