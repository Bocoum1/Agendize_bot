from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass(slots=True, frozen=True)
class Slot:
    """
    Représentation normalisée d'un créneau.

    Tous les détecteurs doivent convertir les données Agendize
    ou navigateur vers ce format unique.
    """
    slot_id: str
    start_at: str
    end_at: Optional[str]
    day: str
    time_label: str
    service_id: Optional[str] = None
    resource_id: Optional[str] = None
    staff_id: Optional[str] = None
    timezone: Optional[str] = None
    source: str = "unknown"
    raw: dict[str, Any] = field(default_factory=dict)

    def unique_key(self) -> str:
        return "|".join(
            [
                self.slot_id,
                self.start_at or "",
                self.end_at or "",
                self.day or "",
                self.time_label or "",
                self.service_id or "",
                self.resource_id or "",
                self.staff_id or "",
            ]
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class DetectionResult:
    """
    Résultat d'une itération de détection.
    """
    slots: list[Slot]
    detector_name: str
    fetched_at: str
    request_meta: dict[str, Any] = field(default_factory=dict)
    raw_payload_excerpt: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "slots": [slot.to_dict() for slot in self.slots],
            "detector_name": self.detector_name,
            "fetched_at": self.fetched_at,
            "request_meta": self.request_meta,
            "raw_payload_excerpt": self.raw_payload_excerpt,
        }


@dataclass(slots=True)
class BookingRequest:
    """
    Entrée du module de réservation.
    """
    slot: Slot
    applicant: dict[str, Any]
    dry_run: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot": self.slot.to_dict(),
            "applicant": self.applicant,
            "dry_run": self.dry_run,
        }


@dataclass(slots=True)
class BookingResult:
    """
    Sortie du module de réservation.
    """
    success: bool
    status: str
    booked_slot: Optional[Slot] = None
    confirmation_code: Optional[str] = None
    message: Optional[str] = None
    screenshot_path: Optional[str] = None
    captcha_detected: bool = False
    requires_human_action: bool = False
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "status": self.status,
            "booked_slot": self.booked_slot.to_dict() if self.booked_slot else None,
            "confirmation_code": self.confirmation_code,
            "message": self.message,
            "screenshot_path": self.screenshot_path,
            "captcha_detected": self.captcha_detected,
            "requires_human_action": self.requires_human_action,
            "meta": self.meta,
        }


@dataclass(slots=True)
class MonitorDiff:
    """
    Diff entre snapshot précédent et snapshot courant.
    """
    new_slots: list[Slot]
    disappeared_slots: list[Slot]
    unchanged_slots: list[Slot]
    previous_count: int
    current_count: int

    @property
    def has_new_slots(self) -> bool:
        return len(self.new_slots) > 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "new_slots": [slot.to_dict() for slot in self.new_slots],
            "disappeared_slots": [slot.to_dict() for slot in self.disappeared_slots],
            "unchanged_slots": [slot.to_dict() for slot in self.unchanged_slots],
            "previous_count": self.previous_count,
            "current_count": self.current_count,
            "has_new_slots": self.has_new_slots,
        }


def utcnow_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"