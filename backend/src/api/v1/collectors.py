import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db, require_role
from collectors.docker_collector import DockerTLSCollectorAdapter
from collectors.fake_collector import FakeCollectorAdapter
from collectors.ssh_collector import SSHCollectorAdapter
from collectors.winrm_collector import WinRMCollectorAdapter
from models.collector import CollectorTarget, TargetType
from models.user import UserRole
from schemas.collector import (
    CollectorTargetCreate,
    CollectorTargetResponse,
    CollectorTargetUpdate,
    TestConnectionResponse,
)

# Admin role required for all collector management endpoints
router = APIRouter(
    prefix="/collectors",
    tags=["collectors"],
    dependencies=[Depends(require_role([UserRole.ADMIN]))],
)


@router.get("", response_model=list[CollectorTargetResponse])
async def list_collector_targets(db: AsyncSession = Depends(get_db)):
    """List all registered collector targets."""
    stmt = select(CollectorTarget).order_by(CollectorTarget.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("", response_model=CollectorTargetResponse, status_code=status.HTTP_201_CREATED)
async def create_collector_target(
    body: CollectorTargetCreate,
    db: AsyncSession = Depends(get_db),
):
    """Register a new collector target (Admin only)."""
    target = CollectorTarget(
        name=body.name,
        target_type=body.target_type,
        host=body.host,
        port=body.port,
        credential_reference=body.credential_reference,
        enabled=body.enabled,
        metadata_={"poll_interval_seconds": body.poll_interval_seconds, **body.metadata},
    )
    db.add(target)
    await db.commit()
    await db.refresh(target)
    return target


@router.get("/{target_id}", response_model=CollectorTargetResponse)
async def get_collector_target(
    target_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get collector target details by ID."""
    stmt = select(CollectorTarget).where(CollectorTarget.id == target_id)
    result = await db.execute(stmt)
    target = result.scalars().first()
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Collector target not found"},
        )
    return target


@router.put("/{target_id}", response_model=CollectorTargetResponse)
async def update_collector_target(
    target_id: uuid.UUID,
    body: CollectorTargetUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update existing collector target."""
    stmt = select(CollectorTarget).where(CollectorTarget.id == target_id)
    result = await db.execute(stmt)
    target = result.scalars().first()
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Collector target not found"},
        )

    if body.name is not None:
        target.name = body.name
    if body.target_type is not None:
        target.target_type = body.target_type
    if body.host is not None:
        target.host = body.host
    if body.port is not None:
        target.port = body.port
    if body.credential_reference is not None:
        target.credential_reference = body.credential_reference
    if body.enabled is not None:
        target.enabled = body.enabled
    if body.poll_interval_seconds is not None:
        meta = dict(target.metadata_ or {})
        meta["poll_interval_seconds"] = body.poll_interval_seconds
        target.metadata_ = meta
    if body.metadata is not None:
        meta = dict(target.metadata_ or {})
        meta.update(body.metadata)
        target.metadata_ = meta

    await db.commit()
    await db.refresh(target)
    return target


@router.delete("/{target_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_collector_target(
    target_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete collector target by ID."""
    stmt = select(CollectorTarget).where(CollectorTarget.id == target_id)
    result = await db.execute(stmt)
    target = result.scalars().first()
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Collector target not found"},
        )
    await db.delete(target)
    await db.commit()


@router.post("/{target_id}/test-connection", response_model=TestConnectionResponse)
async def test_collector_connection(
    target_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Test reachability and authentication of a target without exposing raw credentials."""
    stmt = select(CollectorTarget).where(CollectorTarget.id == target_id)
    result = await db.execute(stmt)
    target = result.scalars().first()
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Collector target not found"},
        )

    # Instantiate adapter according to target type
    if target.target_type == TargetType.SSH:
        adapter = SSHCollectorAdapter(
            target_host=target.host,
            target_port=target.port,
            credential_ref=target.credential_reference,
        )
    elif target.target_type == TargetType.WINRM:
        adapter = WinRMCollectorAdapter(
            target_host=target.host,
            target_port=target.port,
            credential_ref=target.credential_reference,
        )
    elif target.target_type == TargetType.DOCKER_TLS:
        adapter = DockerTLSCollectorAdapter(
            target_host=target.host,
            target_port=target.port,
            credential_ref=target.credential_reference,
        )
    else:
        adapter = FakeCollectorAdapter(
            target_host=target.host,
            target_port=target.port,
            credential_ref=target.credential_reference,
        )

    try:
        success = await adapter.test_connection()
        message = (
            "Connection successful"
            if success
            else "Connection failed or authentication rejected"
        )
    except Exception as e:
        success = False
        message = f"Connection error: {str(e)}"

    return TestConnectionResponse(
        target_id=target.id,
        success=success,
        message=message,
    )


from pydantic import BaseModel, Field
from services.network_discovery_service import scan_subnet_ip_range
from api.deps import get_current_user
from models.user import User


class SubnetScanRequest(BaseModel):
    cidr: str = Field(..., example="10.10.0.0/24", description="CIDR subnet range to auto-scan")


@router.post("/scan-subnet")
async def trigger_subnet_scan(
    body: SubnetScanRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Auto-scan an entire IP Subnet (e.g. 10.10.0.0/24) for active servers and register discovered nodes into Inventory."""
    try:
        res = await scan_subnet_ip_range(db=db, cidr=body.cidr, username=current_user.username)
        return res
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        )
