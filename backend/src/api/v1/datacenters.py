import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db, require_role
from models.node import Node
from models.user import User, UserRole
from schemas.node import (
    AssignHostsRequest,
    DataCenterCreate,
    DataCenterResponse,
    DataCenterUpdate,
    NodeResponse,
)
from services import datacenter_service

router = APIRouter(prefix="/datacenters", tags=["Data Centers"])


@router.get("", response_model=list[DataCenterResponse])
async def list_datacenters(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dcs = await datacenter_service.get_datacenters(db)
    return [DataCenterResponse.model_validate(dc) for dc in dcs]


@router.post("", response_model=DataCenterResponse, status_code=status.HTTP_201_CREATED)
async def create_datacenter(
    req: DataCenterCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN])),
):
    dc_node = await datacenter_service.create_datacenter(
        db=db,
        name=req.name,
        location=req.location,
        metadata=req.metadata,
        admin_user=current_user,
    )
    await db.commit()
    await db.refresh(dc_node)
    return DataCenterResponse.model_validate(dc_node)


@router.get("/{id}", response_model=DataCenterResponse)
async def get_datacenter_detail(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    node = await db.get(Node, id)
    if not node or node.type != "data_center":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data Center '{id}' not found.",
        )
    return DataCenterResponse.model_validate(node)


@router.put("/{id}", response_model=DataCenterResponse)
async def update_datacenter(
    id: uuid.UUID,
    req: DataCenterUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN])),
):
    try:
        updated_dc = await datacenter_service.update_datacenter(
            db=db,
            datacenter_id=id,
            name=req.name,
            location=req.location,
            metadata=req.metadata,
            admin_user=current_user,
        )
        await db.commit()
        await db.refresh(updated_dc)
        return DataCenterResponse.model_validate(updated_dc)
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_datacenter(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN])),
):
    try:
        await datacenter_service.delete_datacenter(
            db=db, datacenter_id=id, admin_user=current_user
        )
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post("/{id}/assign-hosts", response_model=list[NodeResponse])
async def assign_hosts_to_datacenter(
    id: uuid.UUID,
    req: AssignHostsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN])),
):
    try:
        assigned = await datacenter_service.assign_hosts_to_datacenter(
            db=db,
            datacenter_id=id,
            host_ids=req.host_ids,
            admin_user=current_user,
        )
        await db.commit()
        for h in assigned:
            await db.refresh(h)
        return [NodeResponse.model_validate(h) for h in assigned]
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
