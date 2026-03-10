from __future__ import annotations

import logging

import httpx

from app.config import NotificationConfig
from app.models import Slot


class NotificationService:
    def __init__(self, config: NotificationConfig, logger: logging.Logger) -> None:
        self.config = config
        self.logger = logger

    async def notify_new_slots(self, slots: list[Slot]) -> None:
        if not slots:
            return

        lines = ["🚨 Nouveau(x) créneau(x) détecté(s) :"]
        for slot in slots:
            lines.append(f"- {slot.day} à {slot.time_label}")

        message = "\n".join(lines)

        self.logger.info(message)

        if self.config.telegram_enabled:
            await self._send_telegram_message(message)

    async def notify_error(self, error_message: str) -> None:
        message = f"❌ Erreur bot Agendize: {error_message}"
        self.logger.error(message)

        if self.config.telegram_enabled:
            await self._send_telegram_message(message)

    async def notify_status(self, message: str) -> None:
        self.logger.info(message)

        if self.config.telegram_enabled:
            await self._send_telegram_message(message)

    async def _send_telegram_message(self, message: str) -> None:
        if not self.config.telegram_bot_token or not self.config.telegram_chat_id:
            self.logger.warning("Telegram activé mais token/chat_id manquant.")
            return

        url = (
            f"https://api.telegram.org/bot"
            f"{self.config.telegram_bot_token}/sendMessage"
        )

        payload = {
            "chat_id": self.config.telegram_chat_id,
            "text": message,
        }

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
        except Exception as exc:
            self.logger.exception("Échec envoi Telegram: %s", exc)