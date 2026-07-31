import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db, require_role
from models.node import LifecycleStatus, Node, NodeStatus, NodeType, ReviewStatus
from models.user import User, UserRole
from schemas.node import (
    NodeApproveRequest,
    NodeRejectRequest,
    NodeResponse,
    PaginatedNodeResponse,
)
from services import node_service

router = APIRouter(prefix="/nodes", tags=["Nodes"])


@router.get("", response_model=PaginatedNodeResponse)
async def list_nodes(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: str | None = Query(None, description="Search term for name/ip/os"),
    type: NodeType | None = Query(None, description="Filter by node type"),
    status: NodeStatus | None = Query(None, description="Filter by node status"),
    review_status: ReviewStatus | None = Query(None, description="Filter by review status"),
    lifecycle_status: LifecycleStatus | None = Query(None, description="Filter by lifecycle status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total, items = await node_service.get_nodes_paginated(
        db=db,
        page=page,
        page_size=page_size,
        search=search,
        node_type=type,
        status=status,
        review_status=review_status,
        lifecycle_status=lifecycle_status,
    )
    return PaginatedNodeResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[NodeResponse.model_validate(item) for item in items],
    )


@router.get("/{id}", response_model=NodeResponse)
async def get_node_detail(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    node = await db.get(Node, id)
    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node '{id}' not found.",
        )
    return NodeResponse.model_validate(node)


@router.get("/{id}/children", response_model=list[NodeResponse])
async def get_node_children(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    node = await db.get(Node, id)
    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node '{id}' not found.",
        )

    stmt = (
        select(Node)
        .where(
            Node.parent_id == id,
            Node.lifecycle_status == LifecycleStatus.ACTIVE,
        )
        .order_by(Node.name.asc())
    )
    res = await db.execute(stmt)
    children = list(res.scalars().all())
    return [NodeResponse.model_validate(c) for c in children]


@router.post("/{id}/approve", response_model=NodeResponse)
async def approve_node_endpoint(
    id: uuid.UUID,
    req: NodeApproveRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN])),
):
    new_name = req.name if req else None
    try:
        approved_node = await node_service.approve_node(
            db=db, node_id=id, admin_user=current_user, new_name=new_name
        )
        await db.commit()
        await db.refresh(approved_node)
        return NodeResponse.model_validate(approved_node)
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post("/{id}/reject", response_model=NodeResponse)
async def reject_node_endpoint(
    id: uuid.UUID,
    req: NodeRejectRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN])),
):
    reason = req.reason if req else None
    try:
        rejected_node = await node_service.reject_node(
            db=db, node_id=id, admin_user=current_user, reason=reason
        )
        await db.commit()
        await db.refresh(rejected_node)
        return NodeResponse.model_validate(rejected_node)
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post("/{id}/archive", response_model=NodeResponse)
async def archive_node_endpoint(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN])),
):
    try:
        archived_node = await node_service.archive_node(
            db=db, node_id=id, admin_user=current_user
        )
        await db.commit()
        await db.refresh(archived_node)
        return NodeResponse.model_validate(archived_node)
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
