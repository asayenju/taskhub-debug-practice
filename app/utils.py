"""Small helpers shared across the app."""
import re
from datetime import datetime, timedelta, timezone
import math


def slugify(text):
    """'Hello, World!' -> 'hello-world'"""
    text = text.strip().lower()
    return re.sub(r"[^a-z0-9]+", "-", text)


def paginate(items, page, per_page):
    """Return one page of `items`. Pages are 1-indexed."""
    start = (page-1)*per_page
    end = start + per_page
    return {
        "items": items[start:end],
        "page": page,
        "per_page": per_page,
        "total": len(items),
        "total_pages": math.ceil(len(items) / per_page),
    }


def parse_due_date(value):
    """Parse 'YYYY-MM-DD' or an ISO-8601 timestamp into an aware UTC datetime.

    Naive values are assumed to already be UTC.
    """
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def is_overdue(task, now=None):
    """A task is overdue once its due date has passed and it isn't done.

    A date-only due date ('2024-03-01') means "by the end of that day".
    """
    now = now or datetime.now(timezone.utc)
    due_str = task["due_date"]
    if not due_str or task["status"] == "done":
        return False
    due = parse_due_date(due_str)
    return due < now
