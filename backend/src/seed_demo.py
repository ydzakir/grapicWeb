"""Demo seed script for the Infrastructure Monitoring & Auto-Topology app.

Usage (from the `backend/` directory, with ENVIRONMENT=development):
    python -m seed_demo

Idempotent: can be run multiple times without creating duplicates. It populates:
  - A data center group
  - Approved physical / Hyper-V / Docker hosts with VMs and containers
  - A mix of pending nodes awaiting admin review
  - Mixed health statuses (up / warning / down / unknown)
  - A fake collector target so the worker can demonstrate the pipeline
  - An automated report delivery schedule

Demo data must NEVER be activated automatically in a production deployment.
"""
import asyncio
import logging
import os
import sys

os.environ.setdefault("ENVIRONMENT", "development")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("seed_demo")

from sqlalchemy import select

from core.database import AsyncSessionLocal
from core.security import get_password_hash
from models.collector import CollectorTarget, TargetType
from models.node import LifecycleStatus, Node, NodeStatus, NodeType, ReviewStatus
from models.report_schedule import ReportSchedule
from models.user import User, UserRole
from services.node_service import upsert_inventory_node
from services.report_scheduler_service import calculate_next_run_at


async def _seed_nodes(db) -> None:
    # Data center root (admin-managed grouping)
    dc_stmt = select(Node).where(Node.type == NodeType.DATA_CENTER, Node.name == "Jakarta-DC1")
    dc = (await db.execute(dc_stmt)).scalars().first()
    if not dc:
        dc = Node(
            name="Jakarta-DC1",
            type=NodeType.DATA_CENTER,
            status=NodeStatus.UP,
            review_status=ReviewStatus.APPROVED,
            lifecycle_status=LifecycleStatus.ACTIVE,
            metadata_={"location": "JKT-DC01"},
        )
        db.add(dc)
        await db.flush()
        logger.info("Seeded data center Jakarta-DC1")

    hosts = [
        {
            "name": "PHYSICAL-JKT-WEB-01",
            "node_type": NodeType.PHYSICAL_SERVER,
            "ip": "10.10.0.11",
            "os": "Ubuntu 24.04 LTS",
            "status": NodeStatus.UP,
            "cpu": 16,
            "ram": 65536,
            "disk": 1000.0,
        },
        {
            "name": "HYPERV-JKT-APP-01",
            "node_type": NodeType.HYPERV_HOST,
            "ip": "10.10.0.12",
            "os": "Windows Server 2022",
            "status": NodeStatus.UP,
            "cpu": 32,
            "ram": 131072,
            "disk": 4000.0,
        },
        {
            "name": "DOCKER-JKT-MON-01",
            "node_type": NodeType.DOCKER_HOST,
            "ip": "10.10.0.13",
            "os": "Debian 12",
            "status": NodeStatus.WARNING,
            "cpu": 8,
            "ram": 32768,
            "disk": 500.0,
        },
        {
            "name": "PHYSICAL-BDG-DB-01",
            "node_type": NodeType.PHYSICAL_SERVER,
            "ip": "10.10.1.21",
            "os": "CentOS Stream 9",
            "status": NodeStatus.UNKNOWN,
            "cpu": 8,
            "ram": 16384,
            "disk": 2000.0,
        },
    ]

    host_nodes = {}
    for spec in hosts:
        node = await upsert_inventory_node(
            db=db,
            name=spec["name"],
            node_type=spec["node_type"],
            os=spec["os"],
            cpu_cores=spec["cpu"],
            ram_mb=spec["ram"],
            disk_gb=spec["disk"],
            ip_address=spec["ip"],
            status=spec["status"],
            metadata={"demo": True},
        )
        node.review_status = ReviewStatus.APPROVED
        node.parent_id = dc.id
        host_nodes[spec["name"]] = node
        logger.info("Seeded host %s (%s)", spec["name"], spec["status"].value)

    # Approved VMs under the Hyper-V host
    vm_specs = [
        ("VM-JKT-APP-01", "10.10.0.101", NodeStatus.UP, host_nodes["HYPERV-JKT-APP-01"]),
        ("VM-JKT-APP-02", "10.10.0.102", NodeStatus.UP, host_nodes["HYPERV-JKT-APP-01"]),
        ("VM-JKT-DB-01", "10.10.0.103", NodeStatus.DOWN, host_nodes["HYPERV-JKT-APP-01"]),
    ]
    for name, ip, status, parent in vm_specs:
        vm = await upsert_inventory_node(
            db=db,
            name=name,
            node_type=NodeType.HYPERV_VM,
            parent_id=parent.id,
            os="Windows Server 2022",
            cpu_cores=4,
            ram_mb=16384,
            disk_gb=250.0,
            ip_address=ip,
            status=status,
            metadata={"demo": True},
        )
        vm.review_status = ReviewStatus.APPROVED
        logger.info("Seeded VM %s (%s)", name, status.value)

    # Approved containers under the Docker host
    container_specs = [
        ("nginx-proxy", NodeStatus.UP, host_nodes["DOCKER-JKT-MON-01"]),
        ("prometheus", NodeStatus.UP, host_nodes["DOCKER-JKT-MON-01"]),
        ("grafana", NodeStatus.WARNING, host_nodes["DOCKER-JKT-MON-01"]),
    ]
    for name, status, parent in container_specs:
        container = await upsert_inventory_node(
            db=db,
            name=f"{parent.name}/{name}",
            node_type=NodeType.DOCKER_CONTAINER,
            parent_id=parent.id,
            os="Linux",
            cpu_cores=1,
            ram_mb=1024,
            disk_gb=5.0,
            status=status,
            metadata={"demo": True, "container_name": name},
        )
        container.review_status = ReviewStatus.APPROVED
        logger.info("Seeded container %s (%s)", name, status.value)

    # Pending nodes awaiting admin review (from a discovery scan)
    pending_specs = [
        ("PHYSICAL-JKT-NEW-01", "10.10.0.201", NodeType.PHYSICAL_SERVER),
        ("DOCKER-BDG-NEW-01", "10.10.1.202", NodeType.DOCKER_HOST),
    ]
    for name, ip, node_type in pending_specs:
        pending = await upsert_inventory_node(
            db=db,
            name=name,
            node_type=node_type,
            os="Linux",
            cpu_cores=4,
            ram_mb=8192,
            disk_gb=200.0,
            ip_address=ip,
            status=NodeStatus.UP,
            metadata={"demo": True, "discovery_source": "seed_demo"},
        )
        logger.info("Seeded pending node %s (review_status=%s)", name, pending.review_status.value)


async def _seed_fake_target(db) -> None:
    stmt = select(CollectorTarget).where(CollectorTarget.name == "Demo Fake Collector Target")
    existing = (await db.execute(stmt)).scalars().first()
    if existing:
        return

    target = CollectorTarget(
        name="Demo Fake Collector Target",
        target_type=TargetType.FAKE,
        host="demo-fake-host.local",
        port=22,
        credential_reference="demo_fake_cred",
        enabled=True,
        metadata_={"poll_interval_seconds": 60, "simulate_failure_mode": None},
    )
    db.add(target)
    logger.info("Seeded fake collector target 'demo-fake-host.local'")


async def _seed_report_schedule(db) -> None:
    stmt = select(ReportSchedule).where(ReportSchedule.name == "Weekly Executive Summary (Demo)")
    existing = (await db.execute(stmt)).scalars().first()
    if existing:
        return

    now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
    schedule = ReportSchedule(
        name="Weekly Executive Summary (Demo)",
        frequency="weekly",
        report_type="weekly",
        export_format="both",
        recipients={"emails": ["executive@company.com"]},
        is_enabled=True,
        next_run_at=calculate_next_run_at("weekly", now),
    )
    db.add(schedule)
    logger.info("Seeded weekly report schedule")


async def _seed_users(db) -> None:
    users_data = [
        ("admin", "admin@infra.com", "AdminSecurePass123!", UserRole.ADMIN, {"permissions": ["*"]}, {"scopes": ["*"]}),
        ("operator", "operator@infra.com", "OperatorPass123!", UserRole.OPERATOR, {"permissions": ["nodes:read", "nodes:write", "alerts:ack"]}, {"scopes": ["*"]}),
        ("viewer", "viewer@infra.com", "ViewerPass123!", UserRole.VIEWER, {"permissions": ["nodes:read", "alerts:read", "topology:read"]}, {"scopes": ["*"]}),
    ]

    for username, email, raw_password, role, perms, scopes in users_data:
        stmt = select(User).where(User.username == username)
        existing = (await db.execute(stmt)).scalars().first()
        if not existing:
            u = User(
                username=username,
                email=email,
                hashed_password=get_password_hash(raw_password),
                role=role,
                is_active=True,
                custom_permissions=perms,
                allowed_group_scopes=scopes,
            )
            db.add(u)
            logger.info("Seeded user %s (%s)", username, role.value)


async def _seed_edges(db) -> None:
    from models.node import ConnectionType, NodeConnection

    stmt = select(Node)
    result = await db.execute(stmt)
    nodes = {n.name: n for n in result.scalars().all()}

    edges_specs = [
        ("PHYSICAL-JKT-WEB-01", "HYPERV-JKT-APP-01", ConnectionType.NETWORK),
        ("PHYSICAL-JKT-WEB-01", "DOCKER-JKT-MON-01", ConnectionType.NETWORK),
        ("HYPERV-JKT-APP-01", "VM-JKT-APP-01", ConnectionType.HOSTS),
        ("HYPERV-JKT-APP-01", "VM-JKT-APP-02", ConnectionType.HOSTS),
        ("HYPERV-JKT-APP-01", "VM-JKT-DB-01", ConnectionType.HOSTS),
        ("DOCKER-JKT-MON-01", "DOCKER-JKT-MON-01/prometheus", ConnectionType.HOSTS),
    ]

    for src_name, tgt_name, conn_type in edges_specs:
        if src_name in nodes and tgt_name in nodes:
            src_node = nodes[src_name]
            tgt_node = nodes[tgt_name]
            edge_stmt = select(NodeConnection).where(
                NodeConnection.source_node_id == src_node.id,
                NodeConnection.target_node_id == tgt_node.id,
            )
            existing = (await db.execute(edge_stmt)).scalars().first()
            if not existing:
                conn = NodeConnection(
                    source_node_id=src_node.id,
                    target_node_id=tgt_node.id,
                    connection_type=conn_type,
                    metadata_={"provenance": "demo_seed"},
                )
                db.add(conn)
                logger.info("Seeded connection edge: %s -> %s", src_name, tgt_name)


async def _seed_alerts(db) -> None:
    from models.alert import Alert, AlertRule, AlertSeverity, AlertStatus

    # Alert Rule
    rule_stmt = select(AlertRule).where(AlertRule.metric_name == "cpu_usage")
    rule = (await db.execute(rule_stmt)).scalars().first()
    if not rule:
        rule = AlertRule(
            metric_name="cpu_usage",
            warning_threshold=80.0,
            critical_threshold=95.0,
            duration_seconds=300,
            is_enabled=True,
        )
        db.add(rule)
        await db.flush()
        logger.info("Seeded demo AlertRule: cpu_usage > 80% / 95%")

    # Alert on a node
    stmt = select(Node).where(Node.name == "VM-JKT-DB-01")
    target_node = (await db.execute(stmt)).scalars().first()
    if target_node:
        alert_stmt = select(Alert).where(Alert.node_id == target_node.id, Alert.status == AlertStatus.FIRING)
        existing_alert = (await db.execute(alert_stmt)).scalars().first()
        if not existing_alert:
            now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
            alert = Alert(
                node_id=target_node.id,
                rule_id=rule.id,
                severity=AlertSeverity.CRITICAL,
                status=AlertStatus.FIRING,
                message=f"Node {target_node.name} status is DOWN. Immediate investigation required.",
                triggered_at=now,
            )
            db.add(alert)
            logger.info("Seeded firing critical alert for %s", target_node.name)


async def main() -> None:
    from core.database import Base, engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        await _seed_users(db)
        await _seed_nodes(db)
        await _seed_edges(db)
        await _seed_alerts(db)
        await _seed_fake_target(db)
        await _seed_report_schedule(db)
        await db.commit()
    logger.info("Demo seed completed successfully.")


if __name__ == "__main__":
    asyncio.run(main())
