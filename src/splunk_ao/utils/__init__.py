from datetime import UTC, datetime, timezone


def _get_timestamp() -> datetime:
    return datetime.now(UTC)


def _now_ns() -> int:
    return round(_get_timestamp().timestamp() * 1e9)
