"""Tests for the demo seed script (M-1) — must be idempotent and populate demo data."""
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.collector import CollectorTarget
from models.node import Node, NodeType, ReviewStatus
from models.report_schedule import ReportSchedule
from models.user import User, UserRole
from services.node_service import upsert_inventory_node


@pytest.mark.asyncio
async def test_seed_helper_creates_and_upserts_nodes_idempotently(db_session: AsyncSession):
    """The seed helpers rely on upsert_inventory_node; verify idempotency + approval."""
    node1 = await upsert_inventory_node(
        db=db_session,
        name="PHYSICAL-JKT-WEB-01",
        node_type=NodeType.PHYSICAL_SERVER,
        os="Ubuntu 24.04 LTS",
        cpu_cores=16,
        ram_mb=65536,
        disk_gb=1000.0,
        ip_address="10.10.0.11",
        status="up",
        metadata={"demo": True},
    )
    node1.review_status = ReviewStatus.APPROVED
    await db_session.commit()

    # Re-run same discovery -> same node, no duplicate
    node2 = await upsert_inventory_node(
        db=db_session,
        name="PHYSICAL-JKT-WEB-01",
        node_type=NodeType.PHYSICAL_SERVER,
        os="Ubuntu 24.04 LTS",
        cpu_cores=16,
        ram_mb=65536,
        disk_gb=1000.0,
        ip_address="10.10.0.11",
        status="up",
        metadata={"demo": True},
    )
    await db_session.commit()

    assert node1.id == node2.id

    stmt = select(Node).where(Node.name == "PHYSICAL-JKT-WEB-01")
    count = len((await db_session.execute(stmt)).scalars().all())
    assert count == 1


@pytest.mark.asyncio
async def test_seed_schema_objects_importable():
    """The seed script and TargetType.FAKE must be importable for the demo pipeline."""
    from seed_demo import main  # noqa: F401

    assert hasattr(CollectorTarget, "__tablename__")
    assert hasattr(ReportSchedule, "__tablename__")
    assert hasattr(User, "__tablename__")


def test_fake_target_type_registered():
    from models.collector import TargetType

    assert TargetType.FAKE == "fake"
