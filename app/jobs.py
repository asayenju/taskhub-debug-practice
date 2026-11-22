"""Background-job helpers: retries and a small priority queue."""
import heapq
import time


def retry(fn, attempts=3, base_delay=0.1, retry_on=(Exception,), sleep=time.sleep):
    """Call `fn`, retrying on `retry_on` with exponential backoff.

    Re-raises the last error once all attempts are used up.
    """
    last_error = None
    for attempt in range(attempts):
        try:
            return fn()
        except retry_on as exc:
            last_error = exc
            sleep(base_delay * 2 ** attempt)
    raise last_error


class JobQueue:
    """Runs jobs lowest-priority-number first; ties run in the order enqueued."""

    def __init__(self):
        self._heap = []

    def enqueue(self, name, fn, priority=0):
        heapq.heappush(self._heap, (priority, name, fn))

    def run_all(self):
        results = []
        while self._heap:
            _, name, fn = heapq.heappop(self._heap)
            results.append((name, fn()))
        return results


def schedule_reminders(queue, tasks, notify):
    """Queue one reminder job per task."""
    for task in tasks:
        queue.enqueue(f"remind:{task['id']}", lambda: notify(task), priority=1)
