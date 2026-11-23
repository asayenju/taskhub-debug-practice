# Progress log

Goal: reach 9/10 on debugging, problem solving and communication within 4 weeks (started 2026-11-22).
Mode: hints only, no direct answers. Check yourself against `ANSWER_KEY.md` only after you have your own answer.

## Scoreboard

| Date | Failing | Passing | Notes |
|---|---|---|---|
| 2026-11-22 | 32 | 26 | Start (29 baseline + 3 from a `datetime.UTC` mistake) |
| 2026-11-23 | 15 | 43 | All of `tests/test_api.py` passes |

## Bugs fixed

| Area | Symptom | Root cause (your words) | Commit |
|---|---|---|---|
| Auth | Usernames case sensitive | Not normalized to lowercase in register/login | d703e2d |
| Auth | Login reveals whether user exists | Different errors for missing user and wrong password | 7cdae63 |
| Tasks | `created_at` naive | Timestamp had no timezone | 5f462f1 |
| Tasks | Booleans accepted as priority | `bool` is a subclass of `int` | 52ed6a3 |
| Tasks | Patching priority to 0 lost | Falsy `or` | 53b3975 |
| Utils | Wrong page / total_pages | Offset assumed 0-indexed pages; no rounding up | b7119f7 |
| Tasks | SQL injection in search | Search term built into the SQL string | 49f1cf5, 078d0f7, ae7fa32 |
| Tasks | Any user could delete any task | Delete matched on id only | 9c24e51 |
| Stats | Users saw each other's stats | Cache key was the same for everyone | da63cfc |
| Stats | Stats stale after changes | Invalidation used the wrong key / missing in update | 78d688f |

## Still failing (15)

- Auth: constant-time password check, case-insensitive bearer scheme
- Cache: LRU eviction, `get_or_compute` under concurrency
- Jobs: retry final sleep, enqueue order, duplicate names, reminders
- Rate limiter: 3 tests
- Utils: slugify hyphens, `parse_due_date` offsets, due-today overdue
- Webhooks: replayed signature

## Skill ratings (honest, evidence based)

| Skill | Now | Target | Evidence |
|---|---|---|---|
| Debugging | 7 | 9 | Good hypotheses and a good print to prove `compute` never ran. Still sometimes proposes fixes before the cause is confirmed. |
| Problem solving | 7.5 | 9 | Good security instincts (parameterized SQL, 404 over 403, per-user cache key). Needs to check related code (e.g. the invalidation) before declaring done. |
| Communication (commits) | 7 | 9 | Explains the why. Subjects too long, not imperative, typos, several fix-up commits. |

## What to improve next

**Debugging**
1. Write one line before each fix: "The bug is ___ because ___, and I know because ___."
2. Predict which tests will flip before running, and keep a hit rate.
3. Ask what the output you already have rules out before adding new code.
4. Hold fix ideas until the evidence agrees with the cause.

**Problem solving**
1. After a fix, run the tests for the whole feature, not only the one that failed.
2. List every place that touches the same data or key (create, update, delete) and check each.
3. Decide between "fix the cause" and "hide the symptom" explicitly.

**Communication**
1. Subject: short, imperative, about 50 characters. Body: what was wrong, why, why this fix.
2. Reread the diff and message once before committing. Check typos.
3. Use `git commit --amend` for unpushed fixes instead of adding a "previous commit missed..." commit.
4. Comments explain why, not what.

## Weekly scorecard (fill in each Sunday)

| Check | Target | Wk 1 | Wk 2 | Wk 3 | Wk 4 |
|---|---|---|---|---|---|
| Prediction hit rate | 80%+ | | | | |
| Incomplete commits | 0 | | | | |
| Subjects short and imperative | all | | | | |
| Bugs found by reading alone (of 23) | 15 | | | | |
| Bugs fixed with no hints | most | | | | |

## Session log

- **2026-11-22/23:** Fixed 10 issues across auth, tasks, utils, search, delete and stats cache. Learned: `bool` is an `int`, naive vs aware datetimes, off-by-one in pagination, parameterized queries, cache keys and invalidation. Next target: the cache and jobs tests, then rate limiter.
