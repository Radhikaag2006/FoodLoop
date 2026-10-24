from datetime import datetime, timezone


def utcnow():
    """Naive UTC now (avoids the deprecated datetime.utcnow)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


from datetime import timedelta  # noqa: E402

IST = timedelta(hours=5, minutes=30)


def day_start(days_ago=0):
    """Naive-UTC datetime of local (IST) midnight, `days_ago` back."""
    local = utcnow() + IST
    mid = local.replace(hour=0, minute=0, second=0, microsecond=0)
    return mid - IST - timedelta(days=days_ago)


def local_day(dt):
    return (dt + IST).strftime("%Y-%m-%d")


def iso(dt):
    return dt.isoformat(timespec="seconds") + "Z" if dt else None
