from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.models import MonitorDiff, Slot, utcnow_iso


class JSONStateStore:
    """
    Persistance JSON locale.

    Deux fichiers :
    - state.json : métadonnées générales
    - seen_slots.json : snapshot courant + historique minimal
    """

    def __init__(self, state_file: Path, seen_slots_file: Path) -> None:
        self.state_file = state_file
        self.seen_slots_file = seen_slots_file
        self._ensure_files_exist()

    def _ensure_files_exist(self) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.seen_slots_file.parent.mkdir(parents=True, exist_ok=True)

        if not self.state_file.exists():
            self._write_json(
                self.state_file,
                {
                    "created_at": utcnow_iso(),
                    "updated_at": utcnow_iso(),
                    "last_run_at": None,
                    "last_success_at": None,
                    "last_error_at": None,
                    "last_error_message": None,
                    "consecutive_errors": 0,
                    "last_detector": None,
                    "last_snapshot_count": 0,
                },
            )

        if not self.seen_slots_file.exists():
            self._write_json(
                self.seen_slots_file,
                {
                    "created_at": utcnow_iso(),
                    "updated_at": utcnow_iso(),
                    "current_slots": [],
                    "history": [],
                },
            )

    def _read_json(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _write_json(self, path: Path, data: dict[str, Any]) -> None:
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        with tmp_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp_path.replace(path)

    def load_state(self) -> dict[str, Any]:
        return self._read_json(self.state_file)

    def save_state(self, patch: dict[str, Any]) -> None:
        state = self.load_state()
        state.update(patch)
        state["updated_at"] = utcnow_iso()
        self._write_json(self.state_file, state)

    def mark_run_started(self, detector_name: str) -> None:
        self.save_state(
            {
                "last_run_at": utcnow_iso(),
                "last_detector": detector_name,
            }
        )

    def mark_run_success(self, snapshot_count: int) -> None:
        self.save_state(
            {
                "last_success_at": utcnow_iso(),
                "consecutive_errors": 0,
                "last_error_message": None,
                "last_snapshot_count": snapshot_count,
            }
        )

    def mark_run_error(self, error_message: str) -> None:
        state = self.load_state()
        current_errors = int(state.get("consecutive_errors", 0))
        self.save_state(
            {
                "last_error_at": utcnow_iso(),
                "last_error_message": error_message,
                "consecutive_errors": current_errors + 1,
            }
        )

    def load_current_slots(self) -> list[Slot]:
        payload = self._read_json(self.seen_slots_file)
        slots_data = payload.get("current_slots", [])
        return [self._slot_from_dict(item) for item in slots_data]

    def save_current_slots(
        self,
        slots: list[Slot],
        detector_name: str,
        request_meta: dict[str, Any] | None = None,
    ) -> None:
        payload = self._read_json(self.seen_slots_file)
        history = payload.get("history", [])

        history.append(
            {
                "saved_at": utcnow_iso(),
                "detector_name": detector_name,
                "count": len(slots),
                "request_meta": request_meta or {},
            }
        )

        # On borne l'historique pour éviter de faire grossir le fichier à l'infini
        history = history[-100:]

        data = {
            "created_at": payload.get("created_at", utcnow_iso()),
            "updated_at": utcnow_iso(),
            "current_slots": [slot.to_dict() for slot in slots],
            "history": history,
        }
        self._write_json(self.seen_slots_file, data)

    def diff_slots(self, new_slots: list[Slot]) -> MonitorDiff:
        previous_slots = self.load_current_slots()

        previous_map = {slot.unique_key(): slot for slot in previous_slots}
        current_map = {slot.unique_key(): slot for slot in new_slots}

        new_items = [
            current_map[key]
            for key in current_map.keys()
            if key not in previous_map
        ]
        disappeared_items = [
            previous_map[key]
            for key in previous_map.keys()
            if key not in current_map
        ]
        unchanged_items = [
            current_map[key]
            for key in current_map.keys()
            if key in previous_map
        ]

        return MonitorDiff(
            new_slots=sorted(new_items, key=self._slot_sort_key),
            disappeared_slots=sorted(disappeared_items, key=self._slot_sort_key),
            unchanged_slots=sorted(unchanged_items, key=self._slot_sort_key),
            previous_count=len(previous_slots),
            current_count=len(new_slots),
        )

    @staticmethod
    def _slot_sort_key(slot: Slot) -> tuple[str, str, str]:
        return (slot.day or "", slot.start_at or "", slot.time_label or "")

    @staticmethod
    def _slot_from_dict(data: dict[str, Any]) -> Slot:
        return Slot(
            slot_id=data.get("slot_id", ""),
            start_at=data.get("start_at", ""),
            end_at=data.get("end_at"),
            day=data.get("day", ""),
            time_label=data.get("time_label", ""),
            service_id=data.get("service_id"),
            resource_id=data.get("resource_id"),
            staff_id=data.get("staff_id"),
            timezone=data.get("timezone"),
            source=data.get("source", "unknown"),
            raw=data.get("raw", {}),
        )