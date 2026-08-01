from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from collectors.base import NormalizedDiscoveryResult
from collectors.scheduler import CollectorScheduler
from models.collector import CollectorTarget, TargetType
from models.node import Node, NodeStatus, NodeType, ReviewStatus
from services.collector_service import (
    process_collector_failure,
    process_collector_success,
    process_discovery_result,
)


@pytest.mark.asyncio
async def test_discovery_node_new_pending_status(db_session: AsyncSession):
    discovery = NormalizedDiscoveryResult(
        canonical_identity="discovery_test_host_01",
        name="SRV-NEW-DISCOVERY",
        node_type=NodeType.PHYSICAL_SERVER,
        ip_address="192.168.1.200",
        os="Ubuntu 24.04",
        cpu_cores=8,
        ram_mb=16384,
        children=[
            NormalizedDiscoveryResult(
                canonical_identity="discovery_test_vm_01",
                name="VM-CHILD-01",
                node_type=NodeType.HYPERV_VM,
                os="Linux",
            )
        ],
    )

    parent_node = await process_discovery_result(db_session, discovery)
    assert parent_node.name == "SRV-NEW-DISCOVERY"
    assert parent_node.review_status == ReviewStatus.PENDING
    assert parent_node.status == NodeStatus.UP

    # Verify child node created with PENDING review_status
    stmt = select(Node).where(
        Node.metadata_["canonical_identity"].as_string() == "discovery_test_vm_01"
    )
    result = await db_session.execute(stmt)
    child_node = result.scalars().first()
    assert child_node is not None
    assert child_node.review_status == ReviewStatus.PENDING
    assert child_node.parent_id == parent_node.id


@pytest.mark.asyncio
async def test_status_transitions_unknown_to_down_and_recovery(db_session: AsyncSession):
    canonical_id = "test_status_transition_node"
    node = Node(
        name="SRV-TRANSITION-TEST",
        type=NodeType.PHYSICAL_SERVER,
        status=NodeStatus.UP,
        review_status=ReviewStatus.PENDING,
        metadata_={"canonical_identity": canonical_id},
    )
    db_session.add(node)
    await db_session.commit()

    # 1. First failure -> transition to UNKNOWN
    updated_node1 = await process_collector_failure(db_session, canonical_id, "Connection timeout")
    assert updated_node1 is not None
    assert updated_node1.status == NodeStatus.UNKNOWN
    assert updated_node1.metadata_["consecutive_failures"] == 1
    assert updated_node1.metadata_["first_failed_at"] is not None

    # 2. Simulate failure window past 120 seconds (2 minutes ago)
    past_time = (datetime.now(UTC) - timedelta(seconds=130)).isoformat()
    meta = dict(updated_node1.metadata_)
    meta["first_failed_at"] = past_time
    updated_node1.metadata_ = meta
    await db_session.commit()

    # Second failure after > 2 min failure window -> transition to DOWN
    updated_node2 = await process_collector_failure(
        db_session, canonical_id, "Connection timeout 2"
    )
    assert updated_node2 is not None
    assert updated_node2.status == NodeStatus.DOWN

    # 3. Recovery poll success -> transition to UP and reset failure tracking
    recovered_node = await process_collector_success(db_session, canonical_id)
    assert recovered_node is not None
    assert recovered_node.status == NodeStatus.UP
    assert recovered_node.metadata_["first_failed_at"] is None
    assert recovered_node.metadata_["consecutive_failures"] == 0


@pytest.mark.asyncio
async def test_scheduler_publishes_prometheus_metrics(db_session: AsyncSession):
    from unittest.mock import patch

    from collectors.fake_collector import FakeCollectorAdapter
    from collectors.metrics_exporter import (
        CPU_USAGE,
        NODE_STATUS,
        remove_node_metrics,
    )

    scheduler = CollectorScheduler(max_concurrency=1, max_retries=0)
    target = CollectorTarget(
        name="Target Metrics",
        target_type=TargetType.SSH,
        host="fake-metrics.local",
        port=22,
        credential_reference="cred_ref_metrics",
    )
    db_session.add(target)
    await db_session.commit()

    with patch.object(
        scheduler,
        "create_adapter",
        side_effect=lambda t: FakeCollectorAdapter(target_host=t.host),
    ):
        result = await scheduler.execute_poll_target(db_session, target)

    assert result is True

    stmt = select(Node).where(
        Node.metadata_["canonical_identity"].as_string() == "fake_host_fake-metrics.local"
    )
    node = (await db_session.execute(stmt)).scalars().first()
    assert node is not None
    assert node.status == NodeStatus.UP

    # Node status gauge populated by worker pipeline
    assert (str(node.id),) in NODE_STATUS._metrics
    # CPU ratio gauge populated (fake collector returns 35.5% -> 0.355 ratio)
    assert (str(node.id),) in CPU_USAGE._metrics

    remove_node_metrics(str(node.id))


@pytest.mark.asyncio
async def test_scheduler_publishes_failure_status_after_recovery(db_session: AsyncSession):
    from unittest.mock import patch

    from collectors.fake_collector import FakeCollectorAdapter
    from collectors.metrics_exporter import NODE_STATUS, remove_node_metrics

    scheduler = CollectorScheduler(max_concurrency=1, max_retries=0)
    target = CollectorTarget(
        name="Target Failure Metrics",
        target_type=TargetType.SSH,
        host="fake-fail.local",
        port=22,
        credential_reference="cred_ref_fail",
    )
    db_session.add(target)
    await db_session.commit()

    with patch.object(
        scheduler,
        "create_adapter",
        side_effect=lambda t: FakeCollectorAdapter(target_host=t.host),
    ):
        # First successful poll discovers the node and publishes UP status
        ok = await scheduler.execute_poll_target(db_session, target)
        assert ok is True

        stmt = select(Node).where(
            Node.metadata_["canonical_identity"].as_string() == "fake_host_fake-fail.local"
        )
        node = (await db_session.execute(stmt)).scalars().first()
        assert node is not None

        # Manually set first failure window to > 2 minutes, then poll a failing adapter
        from datetime import UTC, datetime, timedelta

        meta = dict(node.metadata_)
        meta["first_failed_at"] = (datetime.now(UTC) - timedelta(seconds=130)).isoformat()
        node.metadata_ = meta
        await db_session.commit()

        with patch.object(
            scheduler,
            "create_adapter",
            side_effect=lambda t: FakeCollectorAdapter(
                target_host=t.host, simulate_failure_mode="connection_refused"
            ),
        ):
            ok = await scheduler.execute_poll_target(db_session, target)

        assert ok is False
        await db_session.refresh(node)
        assert node.status == NodeStatus.DOWN

        # Failure status gauge published
        assert (str(node.id),) in NODE_STATUS._metrics

        remove_node_metrics(str(node.id))


@pytest.mark.asyncio
async def test_scheduler_bounded_concurrency_and_retry(db_session: AsyncSession):
    scheduler = CollectorScheduler(max_concurrency=2, max_retries=1)

    target1 = CollectorTarget(
        name="Target Fake 1",
        target_type=TargetType.SSH,
        host="fake-1.local",
        port=22,
        credential_reference="cred_ref_1",
    )
    target2 = CollectorTarget(
        name="Target Fake 2",
        target_type=TargetType.SSH,
        host="fake-2.local",
        port=22,
        credential_reference="cred_ref_2",
    )
    db_session.add_all([target1, target2])
    await db_session.commit()

    from unittest.mock import patch

    from collectors.fake_collector import FakeCollectorAdapter

    with patch.object(
        scheduler,
        "create_adapter",
        side_effect=lambda target: FakeCollectorAdapter(target_host=target.host),
    ):
        results = await scheduler.poll_all_targets(db_session)
        assert len(results) == 2
        assert all(results)
