from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_DISPLAY_TIMEZONE = "Asia/Shanghai"

TIMEZONE_LABELS: dict[str, str] = {
    "UTC": "UTC",
    "Asia/Shanghai": "北京时间",
    "Asia/Hong_Kong": "香港时间",
    "Asia/Taipei": "台北时间",
    "Asia/Tokyo": "日本时间",
    "Asia/Seoul": "韩国时间",
    "Europe/London": "英国时间",
    "Europe/Paris": "中欧时间",
    "America/New_York": "美国东部时间",
    "America/Chicago": "美国中部时间",
    "America/Denver": "美国山地时间",
    "America/Los_Angeles": "美国西部时间",
}


def get_display_timezone_name(configured_name: str | None) -> str:
    if configured_name:
        try:
            ZoneInfo(configured_name)
            return configured_name
        except ZoneInfoNotFoundError:
            pass
    return DEFAULT_DISPLAY_TIMEZONE


def _get_zone(configured_name: str | None) -> ZoneInfo:
    return ZoneInfo(get_display_timezone_name(configured_name))


def _get_timezone_label(configured_name: str | None, display_dt: datetime) -> str:
    zone_name = get_display_timezone_name(configured_name)
    label = TIMEZONE_LABELS.get(zone_name)
    if label:
        return label

    offset = display_dt.utcoffset()
    if offset is None:
        return zone_name
    return f"UTC{_format_offset(offset)}"


def _format_offset(offset: timedelta) -> str:
    total_minutes = int(offset.total_seconds() // 60)
    sign = "+" if total_minutes >= 0 else "-"
    total_minutes = abs(total_minutes)
    hours, minutes = divmod(total_minutes, 60)
    return f"{sign}{hours:02d}:{minutes:02d}"


def format_mail_display_time(
    date_raw: str, fallback_text: str, configured_name: str | None
) -> str:
    if not date_raw:
        return fallback_text

    try:
        mail_dt = datetime.fromisoformat(date_raw)
    except ValueError:
        return fallback_text

    if mail_dt.tzinfo is None:
        mail_dt = mail_dt.replace(tzinfo=timezone.utc)

    target_zone = _get_zone(configured_name)
    display_dt = mail_dt.astimezone(target_zone)
    timezone_label = _get_timezone_label(configured_name, display_dt)
    return f"{display_dt.strftime('%Y-%m-%d %H:%M')}（{timezone_label}）"


def format_runtime_display_time(date_raw: str, configured_name: str | None) -> str:
    if not date_raw:
        return "尚未检查"

    try:
        runtime_dt = datetime.fromisoformat(date_raw)
    except ValueError:
        return date_raw

    if runtime_dt.tzinfo is None:
        runtime_dt = runtime_dt.replace(tzinfo=timezone.utc)

    target_zone = _get_zone(configured_name)
    display_dt = runtime_dt.astimezone(target_zone)
    timezone_label = _get_timezone_label(configured_name, display_dt)
    return f"{display_dt.strftime('%Y-%m-%d %H:%M:%S')}（{timezone_label}）"