import asyncio
import json

from app.config import load_config
from app.slot_detector import build_slot_detector
from app.state_store import JSONStateStore


async def main() -> None:
    config = load_config()
    detector = build_slot_detector(config)

    store = JSONStateStore(
        state_file=config.storage.state_file,
        seen_slots_file=config.storage.seen_slots_file,
    )

    store.mark_run_started(detector.name)

    result = await detector.fetch_slots()
    diff = store.diff_slots(result.slots)

    print("\n=== DETECTOR RESULT ===")
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2)[:6000])

    print("\n=== DIFF ===")
    print(json.dumps(diff.to_dict(), ensure_ascii=False, indent=2)[:4000])

    store.save_current_slots(
        slots=result.slots,
        detector_name=result.detector_name,
        request_meta=result.request_meta,
    )
    store.mark_run_success(snapshot_count=len(result.slots))


if __name__ == "__main__":
    asyncio.run(main())