import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db
from models.user import User
from schemas.metrics import MetricSeriesResponse
from services import metrics_service

router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.get("", response_model=MetricSeriesResponse)
async def get_node_metrics(
    node_id: uuid.UUID = Query(..., description="Target Node UUID"),
    metric_name: str = Query(
        "cpu_usage",
        description="Metric name allowlisted (cpu_usage, ram_usage, disk_usage, network_in, network_out)",
    ),
    range: str = Query(
        "1h", description="Time range allowlisted (1h, 6h, 24h, 7d, 30d)"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        series = await metrics_service.query_node_metrics(
            db=db,
            node_id=node_id,
            metric_name=metric_name,
            range_str=range,
        )
        return series
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc).strip("'"),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except TimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Prometheus service timed out",
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
