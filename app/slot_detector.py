from __future__ import annotations

from abc import ABC, abstractmethod
from playwright.async_api import async_playwright

from app.config import AppConfig
from app.models import DetectionResult, Slot, utcnow_iso


class BaseSlotDetector(ABC):

    name: str = "base_detector"

    def __init__(self, config: AppConfig):
        self.config = config

    @abstractmethod
    async def fetch_slots(self) -> DetectionResult:
        pass


class PlaywrightSlotDetector(BaseSlotDetector):

    name = "playwright_network"

    async def fetch_slots(self) -> DetectionResult:

        slots = []
        calls = []

        async with async_playwright() as p:

            browser = await p.chromium.launch(headless=True)

            page = await browser.new_page()

            async def handle_response(response):

                if "freeSlots" not in response.url:
                    return

                calls.append(response.url)

                try:
                    data = await response.json()
                except:
                    return

                free = data.get("freeSlots", {})

                for day, times in free.items():

                    for t in times:

                        slot = Slot(
                            slot_id=f"{day}-{t}",
                            start_at=f"{day}T{t}",
                            end_at=None,
                            day=day,
                            time_label=t,
                            source="playwright",
                            raw={"day": day, "time": t},
                        )

                        slots.append(slot)

            page.on("response", handle_response)

            # ouvrir page
            await page.goto(self.config.target_url)

            # attendre widget
            await page.wait_for_timeout(3000)

            # cliquer service
            try:
                await page.get_by_text("Dépôt Passeport Normal").click()
            except:
                pass

            await page.wait_for_timeout(2000)

            # cliquer bouton réserver
            try:
                await page.get_by_text("Réserver").click()
            except:
                pass

            # attendre chargement calendrier
            await page.wait_for_timeout(5000)

            await browser.close()

        return DetectionResult(
            slots=slots,
            detector_name=self.name,
            fetched_at=utcnow_iso(),
            request_meta={"calls": calls},
            raw_payload_excerpt=None,
        )


def build_slot_detector(config: AppConfig):

    return PlaywrightSlotDetector(config)