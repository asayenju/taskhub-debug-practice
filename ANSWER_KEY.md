# ANSWER KEY — spoilers!

Don't open this until you've had a real go. Bugs are grouped by file so you can use it as a hint ladder:
peek at just the **location** column first, then the **symptom**, and only then the cause and fix.

## Quick index

| # | Where | Category |
|---|-------|----------|
| 1 | app/utils.py `slugify` | String handling |
| 2 | app/utils.py `paginate` | Off-by-one |
| 3 | app/utils.py `paginate` | Off-by-one / arithmetic |
| 4 | app/utils.py `parse_due_date` | Dates & timezones |
| 5 | app/cache.py `TTLCache.get` | Data structures |
| 6 | app/ratelimit.py `RateLimiter.allow` | Off-by-one |
| 7 | app/auth.py `verify_password` | Security |
| 8 | app/auth.py `extract_bearer` | HTTP / spec compliance |
| 9 | app/jobs.py `retry` | Control flow |
| 10 | app/jobs.py `JobQueue` | Data structures (heapq) |
| 11 | app/webhooks.py `sign` | Security |
| 12 | app/routes.py `list_tasks` | Security |
| 13 | app/routes.py `delete_task` | Security (IDOR / authz) |
| 14 | app/routes.py `stats` and `invalidate_stats` | Caching / data leak |
| 15 | app/routes.py `update_task` | Caching / staleness |
| 16 | app/routes.py `update_task` | Python gotcha |
| 17 | app/routes.py `valid_priority` | Python gotcha / validation |
| 18 | app/routes.py `create_task` | Dates & timezones |
| 19 | app/utils.py `is_overdue` | Dates & timezones / business logic |
| 20 | app/routes.py `login` | Security (user enumeration) |
| 21 | app/routes.py `register` and `login` | Input normalization |
| 22 | app/jobs.py `schedule_reminders` | Python gotcha |
| 23 | app/cache.py `TTLCache.get_or_compute` | Concurrency |

## 1. slugify leaves leading/trailing hyphens
- **Category:** String handling
- **Where:** app/utils.py `slugify`
- **Symptom:** `slugify("Hello, World!")` returns `"hello-world-"`; task slugs end in a hyphen.
- **Root cause:** The regex turns every non-alphanumeric run into `-`, including at the ends, and nothing trims them.
- **Fix:** `return re.sub(r"[^a-z0-9]+", "-", text).strip("-")`
- **Exposed by:** `test_slugify_has_no_leading_or_trailing_hyphens`

## 2. Pagination is 0-indexed but the API is 1-indexed
- **Category:** Off-by-one
- **Where:** app/utils.py `paginate`
- **Symptom:** `?page=1` skips the first `per_page` items; the last page comes back empty.
- **Root cause:** `start = page * per_page` treats pages as 0-indexed, but the API and the docstring say 1-indexed.
- **Fix:** `start = (page - 1) * per_page`
- **Exposed by:** `test_first_page_returns_first_items`, `test_last_page_is_partial`, `test_list_is_paginated_newest_first`

## 3. total_pages rounds down
- **Category:** Off-by-one / arithmetic
- **Where:** app/utils.py `paginate`
- **Symptom:** 25 items at 10 per page reports 2 pages, so clients never fetch the last 5 items.
- **Root cause:** Floor division. It needs a ceiling.
- **Fix:** `-(-len(items) // per_page)` or `math.ceil(len(items) / per_page)`
- **Exposed by:** `test_total_pages_rounds_up`, `test_list_is_paginated_newest_first`

## 4. Timezone-aware due dates are not converted to UTC
- **Category:** Dates & timezones
- **Where:** app/utils.py `parse_due_date`
- **Symptom:** `2024-03-01T23:00:00-05:00` comes back with a -05:00 offset even though the function promises UTC.
- **Root cause:** Only naive datetimes are touched. Aware ones are returned as-is, so callers that use `.date()` or `.hour` see local values.
- **Fix:** `return dt.astimezone(timezone.utc)` on the aware path.
- **Exposed by:** `test_parse_due_date_converts_offsets_to_utc`

## 5. LRU cache never refreshes recency on read
- **Category:** Data structures
- **Where:** app/cache.py `TTLCache.get`
- **Symptom:** A hot key that is read constantly still gets evicted first. It behaves like FIFO, not LRU.
- **Root cause:** `get` never calls `move_to_end`, so reads don't change eviction order.
- **Fix:** Call `self._data.move_to_end(key)` before returning the value in `get`.
- **Exposed by:** `test_least_recently_used_entry_is_evicted`

## 6. Rate limiter lets through limit+1 requests
- **Category:** Off-by-one
- **Where:** app/ratelimit.py `RateLimiter.allow`
- **Symptom:** With a limit of 3 you can make 4 requests per window.
- **Root cause:** Checks `len(hits) > limit` *before* recording the new hit. It should block once `len(hits) >= limit`.
- **Fix:** `if len(hits) >= self.limit:`
- **Exposed by:** `test_blocks_requests_over_the_limit`, `test_window_slides`, `test_api_returns_429_with_retry_after`

## 7. Password hashes compared with `==`
- **Category:** Security
- **Where:** app/auth.py `verify_password`
- **Symptom:** No visible symptom. A timing side channel lets an attacker learn the hash byte by byte.
- **Root cause:** String `==` returns early on the first differing character. It should be a constant-time comparison.
- **Fix:** `import hmac` and `return hmac.compare_digest(candidate, stored)`
- **Exposed by:** `test_password_check_is_constant_time`

## 8. Bearer scheme matched case-sensitively
- **Category:** HTTP / spec compliance
- **Where:** app/auth.py `extract_bearer`
- **Symptom:** Clients that send `Authorization: bearer <token>` get 401s.
- **Root cause:** Auth scheme names are case-insensitive (RFC 7235). The code compares against the literal `Bearer`.
- **Fix:** `parts[0].lower() != "bearer"`
- **Exposed by:** `test_bearer_scheme_is_case_insensitive`

## 9. retry() sleeps after the final failed attempt
- **Category:** Control flow
- **Where:** app/jobs.py `retry`
- **Symptom:** When a job is going to fail anyway, it still waits the longest backoff before raising.
- **Root cause:** `sleep` runs unconditionally inside the `except`, including on the last attempt.
- **Fix:** Only sleep `if attempt < attempts - 1`.
- **Exposed by:** `test_retry_gives_up_without_a_pointless_final_sleep`

## 10. Job queue ties broken by name, and can crash
- **Category:** Data structures (heapq)
- **Where:** app/jobs.py `JobQueue`
- **Symptom:** Same-priority jobs run alphabetically instead of FIFO. Two jobs with the same name raise `TypeError: '<' not supported between instances of 'function' and 'function'`.
- **Root cause:** Heap entries are `(priority, name, fn)`. On a priority tie Python compares `name`, and on a name tie it compares the functions.
- **Fix:** Add a monotonically increasing counter: `(priority, next(self._seq), name, fn)` with `self._seq = itertools.count()`.
- **Exposed by:** `test_equal_priority_jobs_run_in_the_order_they_were_enqueued`, `test_jobs_with_the_same_name_do_not_crash_the_queue`

## 11. Webhook timestamp is not covered by the signature (replay)
- **Category:** Security
- **Where:** app/webhooks.py `sign`
- **Symptom:** An attacker who captures one delivery can replay it forever by attaching a fresh `X-Timestamp`.
- **Root cause:** The 5-minute freshness check is meaningless because `timestamp` is never part of the signed message.
- **Fix:** Sign `f"{timestamp}.".encode() + body`.
- **Exposed by:** `test_replayed_signature_cannot_be_given_a_fresh_timestamp`

## 12. SQL injection in task search
- **Category:** Security
- **Where:** app/routes.py `list_tasks`
- **Symptom:** `GET /tasks?q=%' OR 1=1 --` returns other users' tasks.
- **Root cause:** `q` is interpolated into the SQL with an f-string. The injected `OR` also defeats the `owner_id` filter.
- **Fix:** `sql += " AND title LIKE ?"` and `params.append(f"%{q}%")`
- **Exposed by:** `test_search_input_cannot_escape_the_query`

## 13. Any user can delete any task (missing ownership check)
- **Category:** Security (IDOR / authz)
- **Where:** app/routes.py `delete_task`
- **Symptom:** User B can delete user A's tasks by guessing integer IDs.
- **Root cause:** GET and PATCH go through `load_task`, which filters by `owner_id`. DELETE runs its own query by `id` only.
- **Fix:** `DELETE FROM tasks WHERE id = ? AND owner_id = ?` with `(task_id, g.user_id)`.
- **Exposed by:** `test_users_cannot_delete_each_others_tasks`

## 14. Stats cache key is global, not per user
- **Category:** Caching / data leak
- **Where:** app/routes.py `stats` and `invalidate_stats`
- **Symptom:** After Alice loads `/stats`, Bob sees Alice's counts for the next 30 seconds.
- **Root cause:** The cache key is the constant `"stats"`, shared by every user.
- **Fix:** Key on the user in both places: `f"stats:{g.user_id}"`.
- **Exposed by:** `test_stats_are_per_user`

## 15. Stats cache not invalidated on update
- **Category:** Caching / staleness
- **Where:** app/routes.py `update_task`
- **Symptom:** Mark a task done, and `/stats` keeps showing the old counts until the TTL expires.
- **Root cause:** Create and delete call `invalidate_stats()`. PATCH doesn't.
- **Fix:** Call `invalidate_stats()` after the commit in `update_task`.
- **Exposed by:** `test_stats_reflect_status_changes_immediately`

## 16. Priority 0 can't be set via PATCH (falsy `or`)
- **Category:** Python gotcha
- **Where:** app/routes.py `update_task`
- **Symptom:** `PATCH {"priority": 0}` silently keeps the old priority.
- **Root cause:** `data.get("priority") or task["priority"]` treats `0` as "not provided".
- **Fix:** `data.get("priority", task["priority"])`
- **Exposed by:** `test_priority_can_be_patched_to_zero`

## 17. `True`/`False` accepted as a priority
- **Category:** Python gotcha / validation
- **Where:** app/routes.py `valid_priority`
- **Symptom:** `{"priority": true}` is stored as `1`.
- **Root cause:** `bool` is a subclass of `int`, so `isinstance(True, int)` is `True`.
- **Fix:** Add `and not isinstance(value, bool)`.
- **Exposed by:** `test_booleans_are_not_valid_priorities`

## 18. created_at uses naive local time
- **Category:** Dates & timezones
- **Where:** app/routes.py `create_task`
- **Symptom:** `created_at` has no offset and shifts with the server's timezone. Clients can't tell what instant it means.
- **Root cause:** `datetime.now()` is naive local time. Everything else in the app is UTC.
- **Fix:** `datetime.now(timezone.utc).isoformat()` (and import `timezone`).
- **Exposed by:** `test_created_at_is_timezone_aware_utc`

## 19. Date-only due dates count as overdue all day
- **Category:** Dates & timezones / business logic
- **Where:** app/utils.py `is_overdue`
- **Symptom:** A task due `2024-03-01` shows as overdue at 00:00:01 on March 1st.
- **Root cause:** `parse_due_date("2024-03-01")` is midnight, so it's "past" for 24 hours. The docstring says date-only means "by the end of that day".
- **Fix:** If the string is date-only (`len(due_str) == 10`), add one day before comparing.
- **Exposed by:** `test_task_due_today_is_not_overdue_yet`

## 20. Login reveals whether a username exists
- **Category:** Security (user enumeration)
- **Where:** app/routes.py `login`
- **Symptom:** Unknown user gets `404 unknown user`, wrong password gets `401 wrong password`.
- **Root cause:** Different status codes and messages let an attacker enumerate valid usernames.
- **Fix:** Return the same `error("invalid credentials", 401)` for both.
- **Exposed by:** `test_login_does_not_reveal_whether_a_user_exists`

## 21. Usernames are case-sensitive
- **Category:** Input normalization
- **Where:** app/routes.py `register` and `login`
- **Symptom:** "Alice" and "alice" can both register, which is confusing and a spoofing risk.
- **Root cause:** Usernames are stored and looked up exactly as typed.
- **Fix:** Normalize with `username.strip().lower()` in both `register` (the INSERT) and `login` (the lookup).
- **Exposed by:** `test_usernames_are_case_insensitive`, `test_login_works_with_any_username_casing`

## 22. Late-binding closure in schedule_reminders
- **Category:** Python gotcha
- **Where:** app/jobs.py `schedule_reminders`
- **Symptom:** Every reminder notifies the *last* task.
- **Root cause:** `lambda: notify(task)` looks up `task` when it runs, after the loop has finished.
- **Fix:** Bind it now: `lambda task=task: notify(task)` (or `functools.partial`).
- **Exposed by:** `test_each_reminder_notifies_its_own_task`

## 23. Cache stampede: get_or_compute is check-then-act
- **Category:** Concurrency
- **Where:** app/cache.py `TTLCache.get_or_compute`
- **Symptom:** Under concurrent requests the expensive computation runs several times for the same key.
- **Root cause:** `get` and `set` are individually locked, but the miss check, the compute and the store aren't atomic together.
- **Fix:** Hold `self._lock` (it's an `RLock`) around the whole method body.
- **Exposed by:** `test_get_or_compute_runs_once_under_concurrency`
