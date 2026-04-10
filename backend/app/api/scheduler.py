import structlog
from fastapi import APIRouter, Depends

from backend.app.core.deps import get_current_user
from backend.app.models.user import User
from backend.app.services.scheduler import scheduler_service

router = APIRouter(prefix="/scheduler", tags=["scheduler"])
logger = structlog.get_logger()


@router.post("/trigger")
async def trigger_orchestrator(current_user: User = Depends(get_current_user)):
    task_id = await scheduler_service.trigger_orchestrator()
    logger.info("scheduler_triggered", user_id=str(current_user.id))
    return {
        "message": "Research Orchestrator triggered.",
        "task_id": task_id,
    }


@router.get("/status")
async def get_scheduler_status(current_user: User = Depends(get_current_user)):
    return scheduler_service.get_status()
