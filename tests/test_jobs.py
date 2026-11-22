import pytest

from app.jobs import JobQueue, retry, schedule_reminders


def test_retry_returns_first_success():
    attempts = []

    def flaky():
        attempts.append(1)
        if len(attempts) < 3:
            raise ConnectionError("boom")
        return "ok"

    sleeps = []
    assert retry(flaky, attempts=5, base_delay=1, sleep=sleeps.append) == "ok"
    assert sleeps == [1, 2]


def test_retry_gives_up_without_a_pointless_final_sleep():
    sleeps = []

    def always_fails():
        raise ConnectionError("down")

    with pytest.raises(ConnectionError):
        retry(always_fails, attempts=3, base_delay=0.5, sleep=sleeps.append)
    assert sleeps == [0.5, 1.0]


def test_retry_does_not_catch_other_errors():
    def bad():
        raise KeyError("nope")

    with pytest.raises(KeyError):
        retry(bad, retry_on=(ConnectionError,), sleep=lambda s: None)


def test_lower_priority_number_runs_first():
    q = JobQueue()
    q.enqueue("low", lambda: 1, priority=5)
    q.enqueue("high", lambda: 2, priority=0)
    assert [name for name, _ in q.run_all()] == ["high", "low"]


def test_equal_priority_jobs_run_in_the_order_they_were_enqueued():
    q = JobQueue()
    q.enqueue("zeta", lambda: 1)
    q.enqueue("alpha", lambda: 2)
    q.enqueue("mid", lambda: 3)
    assert [name for name, _ in q.run_all()] == ["zeta", "alpha", "mid"]


def test_jobs_with_the_same_name_do_not_crash_the_queue():
    q = JobQueue()
    q.enqueue("dup", lambda: 1)
    q.enqueue("dup", lambda: 2)
    assert [result for _, result in q.run_all()] == [1, 2]


def test_each_reminder_notifies_its_own_task():
    notified = []
    q = JobQueue()
    schedule_reminders(q, [{"id": 1}, {"id": 2}, {"id": 3}], lambda t: notified.append(t["id"]))
    q.run_all()
    assert notified == [1, 2, 3]
