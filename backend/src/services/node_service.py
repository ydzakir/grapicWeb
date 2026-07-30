import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.node import Node


async def check_hierarchy_cycle(
    db: AsyncSession, node_id: uuid.UUID, proposed_parent_id: uuid.UUID | None
) -> None:
    """
    Check if assigning proposed_parent_id to node_id would create a hierarchy cycle.
    Raises ValueError if a cycle is detected.
    """
    if proposed_parent_id is None:
        return

    if node_id == proposed_parent_id:
        raise ValueError("Hierarchy cycle detected: A node cannot be its own parent.")

    # Walk up the ancestor tree starting from proposed_parent_id
    current_id: uuid.UUID | None = proposed_parent_id
    visited: set[uuid.UUID] = {node_id}

    while current_id is not None:
        if current_id in visited:
            raise ValueError(
                f"Hierarchy cycle detected: Node '{node_id}' "
                f"is an ancestor of proposed parent '{proposed_parent_id}'."
            )
        visited.add(current_id)

        stmt = select(Node.parent_id).where(Node.id == current_id)
        result = await db.execute(stmt)
        parent_id_record = result.scalars().first()
        current_id = parent_id_record
