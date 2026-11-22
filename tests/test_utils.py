from datetime import datetime, timezone

from app.utils import is_overdue, paginate, parse_due_date, slugify


def test_slugify_lowercases_and_joins_words():
    assert slugify("Write the Report") == "write-the-report"


def test_slugify_has_no_leading_or_trailing_hyphens():
    assert slugify("Hello, World!") == "hello-world"
    assert slugify("  --Fix bug #42--  ") == "fix-bug-42"


def test_first_page_returns_first_items():
    page = paginate(list(range(25)), page=1, per_page=10)
    assert page["items"] == list(range(10))


def test_last_page_is_partial():
    page = paginate(list(range(25)), page=3, per_page=10)
    assert page["items"] == [20, 21, 22, 23, 24]


def test_total_pages_rounds_up():
    assert paginate(list(range(25)), 1, 10)["total_pages"] == 3
    assert paginate(list(range(20)), 1, 10)["total_pages"] == 2
    assert paginate([], 1, 10)["total_pages"] == 0


def test_parse_due_date_naive_is_utc():
    assert parse_due_date("2024-03-01").isoformat() == "2024-03-01T00:00:00+00:00"


def test_parse_due_date_converts_offsets_to_utc():
    assert parse_due_date("2024-03-01T23:00:00-05:00").isoformat() == "2024-03-02T04:00:00+00:00"


def test_task_due_today_is_not_overdue_yet():
    now = datetime(2024, 3, 1, 10, 0, tzinfo=timezone.utc)
    task = {"due_date": "2024-03-01", "status": "todo"}
    assert is_overdue(task, now=now) is False


def test_task_due_yesterday_is_overdue():
    now = datetime(2024, 3, 2, 0, 0, 1, tzinfo=timezone.utc)
    assert is_overdue({"due_date": "2024-03-01", "status": "todo"}, now=now) is True


def test_done_tasks_are_never_overdue():
    now = datetime(2025, 1, 1, tzinfo=timezone.utc)
    assert is_overdue({"due_date": "2024-03-01", "status": "done"}, now=now) is False
