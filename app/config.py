from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


def _get_env(name: str, default: Optional[str] = None, required: bool = False) -> str:
    value = os.getenv(name, default)
    if required and (value is None or value == ""):
        raise ValueError(f"Missing required environment variable: {name}")
    return value if value is not None else ""


def _get_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"Environment variable {name} must be an integer") from exc


@dataclass(slots=True)
class AgendizeAPIConfig:
    """
    Configuration API Agendize.

    Remarque:
    - Certains sites exposent directement ces paramètres.
    - D'autres les encapsulent dans une session ou un widget signé.
    - On laisse donc ces champs optionnels au départ.
    """
    base_url: str
    company_id: str
    service_id: str
    resource_id: str
    staff_id: Optional[str]
    timezone: str
    start_date_offset_days: int
    search_window_days: int
    use_http_detection: bool


@dataclass(slots=True)
class BrowserConfig:
    headless: bool
    slow_mo_ms: int
    navigation_timeout_ms: int
    action_timeout_ms: int
    browser_state_path: Path
    screenshot_dir: Path
    trace_dir: Path


@dataclass(slots=True)
class MonitorConfig:
    poll_interval_seconds: int
    jitter_seconds: int
    max_consecutive_errors: int
    auto_book: bool
    dry_run: bool


@dataclass(slots=True)
class NotificationConfig:
    telegram_enabled: bool
    telegram_bot_token: Optional[str]
    telegram_chat_id: Optional[str]
    email_enabled: bool
    smtp_host: Optional[str]
    smtp_port: int
    smtp_username: Optional[str]
    smtp_password: Optional[str]
    email_from: Optional[str]
    email_to: Optional[str]


@dataclass(slots=True)
class StorageConfig:
    data_dir: Path
    logs_dir: Path
    state_file: Path
    seen_slots_file: Path


@dataclass(slots=True)
class AppConfig:
    target_url: str
    log_level: str
    agendize: AgendizeAPIConfig
    browser: BrowserConfig
    monitor: MonitorConfig
    notifications: NotificationConfig
    storage: StorageConfig


def load_config() -> AppConfig:
    data_dir = Path(_get_env("DATA_DIR", "./data")).resolve()
    logs_dir = Path(_get_env("LOGS_DIR", "./logs")).resolve()

    browser_state_path = data_dir / "browser_state.json"
    screenshot_dir = data_dir / "screenshots"
    trace_dir = data_dir / "traces"
    state_file = data_dir / "state.json"
    seen_slots_file = data_dir / "seen_slots.json"

    data_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    trace_dir.mkdir(parents=True, exist_ok=True)

    agendize = AgendizeAPIConfig(
        base_url=_get_env("AGENDIZE_BASE_URL", "https://api.agendize.com/api/2.1"),
        company_id=_get_env("AGENDIZE_COMPANY_ID", ""),
        service_id=_get_env("AGENDIZE_SERVICE_ID", ""),
        resource_id=_get_env("AGENDIZE_RESOURCE_ID", ""),
        staff_id=_get_env("AGENDIZE_STAFF_ID", None),
        timezone=_get_env("AGENDIZE_TIMEZONE", "Europe/Paris"),
        start_date_offset_days=_get_int("AGENDIZE_START_DATE_OFFSET_DAYS", 0),
        search_window_days=_get_int("AGENDIZE_SEARCH_WINDOW_DAYS", 30),
        use_http_detection=_get_bool("USE_HTTP_DETECTION", True),
    )

    browser = BrowserConfig(
        headless=_get_bool("PLAYWRIGHT_HEADLESS", True),
        slow_mo_ms=_get_int("PLAYWRIGHT_SLOW_MO_MS", 0),
        navigation_timeout_ms=_get_int("PLAYWRIGHT_NAVIGATION_TIMEOUT_MS", 30000),
        action_timeout_ms=_get_int("PLAYWRIGHT_ACTION_TIMEOUT_MS", 15000),
        browser_state_path=browser_state_path,
        screenshot_dir=screenshot_dir,
        trace_dir=trace_dir,
    )

    monitor = MonitorConfig(
        poll_interval_seconds=_get_int("POLL_INTERVAL_SECONDS", 20),
        jitter_seconds=_get_int("POLL_JITTER_SECONDS", 3),
        max_consecutive_errors=_get_int("MAX_CONSECUTIVE_ERRORS", 20),
        auto_book=_get_bool("AUTO_BOOK", False),
        dry_run=_get_bool("DRY_RUN", True),
    )

    notifications = NotificationConfig(
        telegram_enabled=_get_bool("TELEGRAM_ENABLED", False),
        telegram_bot_token=_get_env("TELEGRAM_BOT_TOKEN", None),
        telegram_chat_id=_get_env("TELEGRAM_CHAT_ID", None),
        email_enabled=_get_bool("EMAIL_ENABLED", False),
        smtp_host=_get_env("SMTP_HOST", None),
        smtp_port=_get_int("SMTP_PORT", 587),
        smtp_username=_get_env("SMTP_USERNAME", None),
        smtp_password=_get_env("SMTP_PASSWORD", None),
        email_from=_get_env("EMAIL_FROM", None),
        email_to=_get_env("EMAIL_TO", None),
    )

    storage = StorageConfig(
        data_dir=data_dir,
        logs_dir=logs_dir,
        state_file=state_file,
        seen_slots_file=seen_slots_file,
    )

    config = AppConfig(
        target_url=_get_env("TARGET_URL", required=True),
        log_level=_get_env("LOG_LEVEL", "INFO").upper(),
        agendize=agendize,
        browser=browser,
        monitor=monitor,
        notifications=notifications,
        storage=storage,
    )

    validate_config(config)
    return config


def validate_config(config: AppConfig) -> None:
    if config.monitor.poll_interval_seconds <= 0:
        raise ValueError("POLL_INTERVAL_SECONDS must be > 0")

    if config.monitor.jitter_seconds < 0:
        raise ValueError("POLL_JITTER_SECONDS must be >= 0")

    if config.agendize.search_window_days <= 0:
        raise ValueError("AGENDIZE_SEARCH_WINDOW_DAYS must be > 0")

    if config.notifications.telegram_enabled:
        if not config.notifications.telegram_bot_token:
            raise ValueError("TELEGRAM_ENABLED=true but TELEGRAM_BOT_TOKEN is missing")
        if not config.notifications.telegram_chat_id:
            raise ValueError("TELEGRAM_ENABLED=true but TELEGRAM_CHAT_ID is missing")

    if config.notifications.email_enabled:
        required = {
            "SMTP_HOST": config.notifications.smtp_host,
            "SMTP_USERNAME": config.notifications.smtp_username,
            "SMTP_PASSWORD": config.notifications.smtp_password,
            "EMAIL_FROM": config.notifications.email_from,
            "EMAIL_TO": config.notifications.email_to,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ValueError(
                f"EMAIL_ENABLED=true but missing configuration values: {', '.join(missing)}"
            )

    if config.monitor.auto_book and config.monitor.dry_run:
        # Cas permis, mais on veut éviter l'ambiguïté.
        # dry_run gagne toujours.
        pass