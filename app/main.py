from __future__ import annotations

import asyncio

from app.config import load_config
from app.logger import setup_logger
from app.notification_service import NotificationService
from app.slot_detector import build_slot_detector
from app.slot_monitor import SlotMonitor
from app.state_store import JSONStateStore


async def main() -> None:
    config = load_config()
    logger = setup_logger(config.log_level, config.storage.logs_dir)

    detector = build_slot_detector(config)
    store = JSONStateStore(
        state_file=config.storage.state_file,
        seen_slots_file=config.storage.seen_slots_file,
    )
    notifier = NotificationService(config.notifications, logger)

    monitor = SlotMonitor(
        detector=detector,
        store=store,
        notifier=notifier,
        logger=logger,
        poll_interval_seconds=config.monitor.poll_interval_seconds,
        jitter_seconds=config.monitor.jitter_seconds,
        max_consecutive_errors=config.monitor.max_consecutive_errors,
    )

    await monitor.run_forever()


if __name__ == "__main__":
    asyncio.run(main())