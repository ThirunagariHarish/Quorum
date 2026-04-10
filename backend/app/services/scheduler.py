from __future__ import annotations

from typing import Optional

from datetime import datetime, timezone

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = structlog.get_logger()


async def _run_orchestrator():
    logger.info("orchestrator_run_started", triggered_at=datetime.now(timezone.utc).isoformat())
    # Placeholder: actual orchestrator invocation goes here


class SchedulerService:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._last_run: Optional[datetime] = None
        self._last_status: str = "idle"

    def start(
        self,
        morning_hour: int = 6,
        morning_minute: int = 0,
        evening_hour: int = 18,
        evening_minute: int = 0,
    ):
        self.scheduler.add_job(
            self._wrapped_run,
            CronTrigger(hour=morning_hour, minute=morning_minute),
            id="morning_run",
            replace_existing=True,
        )
        self.scheduler.add_job(
            self._wrapped_run,
            CronTrigger(hour=evening_hour, minute=evening_minute),
            id="evening_run",
            replace_existing=True,
        )
        self.scheduler.start()
        logger.info(
            "scheduler_started",
            morning=f"{morning_hour:02d}:{morning_minute:02d}",
            evening=f"{evening_hour:02d}:{evening_minute:02d}",
        )

    async def _wrapped_run(self):
        self._last_run = datetime.now(timezone.utc)
        try:
            await _run_orchestrator()
            self._last_status = "completed"
        except Exception as e:
            self._last_status = "failed"
            logger.error("orchestrator_run_failed", error=str(e))

    async def trigger_orchestrator(self) -> Optional[str]:
        await self._wrapped_run()
        return None

    def get_status(self) -> dict:
        jobs = {j.id: j for j in self.scheduler.get_jobs()}

        morning_next = None
        evening_next = None
        if "morning_run" in jobs:
            morning_next = jobs["morning_run"].next_run_time
        if "evening_run" in jobs:
            evening_next = jobs["evening_run"].next_run_time

        return {
            "is_running": self.scheduler.running,
            "next_morning_run": morning_next.isoformat() if morning_next else None,
            "next_evening_run": evening_next.isoformat() if evening_next else None,
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "last_run_status": self._last_status,
        }

    def shutdown(self):
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("scheduler_shutdown")


scheduler_service = SchedulerService()
