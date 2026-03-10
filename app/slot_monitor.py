from __future__ import annotations

import asyncio
import logging
import random

from app.models import DetectionResult, MonitorDiff
from app.notification_service import NotificationService
from app.slot_detector import BaseSlotDetector
from app.state_store import JSONStateStore


class SlotMonitor:
    def __init__(
        self,
        detector: BaseSlotDetector,
        store: JSONStateStore,
        notifier: NotificationService,
        logger: logging.Logger,
        poll_interval_seconds: int,
        jitter_seconds: int,
        max_consecutive_errors: int,
    ) -> None:
        self.detector = detector
        self.store = store
        self.notifier = notifier
        self.logger = logger
        self.poll_interval_seconds = poll_interval_seconds
        self.jitter_seconds = jitter_seconds
        self.max_consecutive_errors = max_consecutive_errors

    async def run_forever(self) -> None:
        self.logger.info("Démarrage du monitor de slots.")
        await self.notifier.notify_status("🤖 Bot Agendize démarré.")

        while True:
            try:
                await self.run_once()
            except Exception as exc:
                error_message = f"{type(exc).__name__}: {exc}"
                self.store.mark_run_error(error_message)
                self.logger.exception("Erreur pendant run_once: %s", exc)
                await self.notifier.notify_error(error_message)

                state = self.store.load_state()
                consecutive_errors = int(state.get("consecutive_errors", 0))

                if consecutive_errors >= self.max_consecutive_errors:
                    fatal_msg = (
                        f"⛔ Arrêt du bot après {consecutive_errors} erreurs consécutives."
                    )
                    self.logger.error(fatal_msg)
                    await self.notifier.notify_error(fatal_msg)
                    raise

            sleep_seconds = self._compute_sleep_duration()
            self.logger.info("Prochaine vérification dans %s sec.", sleep_seconds)
            await asyncio.sleep(sleep_seconds)

    async def run_once(self) -> DetectionResult:
        self.store.mark_run_started(self.detector.name)
        self.logger.info("Lancement détection avec %s", self.detector.name)

        result = await self.detector.fetch_slots()
        diff = self.store.diff_slots(result.slots)

        self._log_result(result, diff)

        if diff.has_new_slots:
            await self.notifier.notify_new_slots(diff.new_slots)

        self.store.save_current_slots(
            slots=result.slots,
            detector_name=result.detector_name,
            request_meta=result.request_meta,
        )
        self.store.mark_run_success(snapshot_count=len(result.slots))

        return result

    def _log_result(self, result: DetectionResult, diff: MonitorDiff) -> None:
        self.logger.info(
            "Détection terminée | detector=%s | slots=%s | new=%s | disappeared=%s",
            result.detector_name,
            len(result.slots),
            len(diff.new_slots),
            len(diff.disappeared_slots),
        )

        if result.slots:
            for slot in result.slots:
                self.logger.info(
                    "Slot détecté | day=%s | time=%s | source=%s",
                    slot.day,
                    slot.time_label,
                    slot.source,
                )

    def _compute_sleep_duration(self) -> int:
        if self.jitter_seconds <= 0:
            return self.poll_interval_seconds

        jitter = random.randint(0, self.jitter_seconds)
        return self.poll_interval_seconds + jitter