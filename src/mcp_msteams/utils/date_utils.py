from datetime import datetime, timedelta, timezone


def utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def days_ago(n: int) -> str:
    dt = utc_now() - timedelta(days=n)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def graph_date_filter(field: str, days: int) -> str:
    since = days_ago(days)
    return f"{field} ge {since}"
