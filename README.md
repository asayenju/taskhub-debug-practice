# TaskHub: debugging practice

A small but realistic multi-user task manager API (Flask + SQLite) with **23 planted bugs**.
Everything is in one repo. The bugs are the kind that come up in interviews and code reviews:

- off-by-one errors and arithmetic
- timezone and date handling
- Python gotchas (late-binding closures, falsy `or`, `bool` is an `int`)
- caching (staleness, key collisions, stampedes)
- security (SQL injection, missing authorization, replay attacks, user enumeration, timing attacks)
- concurrency and data-structure mistakes

## Setup

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest          # 29 failures to start
.venv/bin/python run.py             # serves on http://localhost:5001
```

## Layout

```
app/
  __init__.py   app factory, rate-limit hook
  routes.py     accounts, tasks CRUD, stats, webhook endpoint
  auth.py       password hashing, bearer tokens
  cache.py      TTL + LRU cache
  ratelimit.py  sliding-window limiter
  jobs.py       retry helper and priority job queue
  webhooks.py   HMAC signature verification
  utils.py      slugify, pagination, date parsing
  db.py         SQLite
tests/          one file per area; failing tests describe the *expected* behaviour
ANSWER_KEY.md   spoilers. Every bug, its cause and its fix
```

## Ways to practice

1. **Test-driven (easiest).** Run the suite and work through the failures one at a time. For each, explain out loud
   what's wrong and why *before* you change anything.
2. **Code-review mode (closest to a real interview).** Read the code *without* running the tests and write down every bug you
   can find. Time-box it to 30 minutes, then check yourself against the test failures and the key.
3. **Black-box mode.** Run the server and hit it with `curl` or a REST client. Look for behavior that's wrong, then find it in the code.
   This is the hardest mode, because several bugs only show up with two users or a repeated request.
4. **Hint ladder.** If you get stuck, open `ANSWER_KEY.md`, read only the *Quick index* row for the bug, and try again.

When you fix a bug, the failing tests that disappear should be the ones you expected. If other tests change at the same
time, work out why.

## Interview habit to build

For each bug, practice saying four things: **symptom → how you reproduced it → root cause → fix, plus how you'd stop it coming back**
(a test, a lint rule, a code-review checklist item).

## Tip

Work on a branch (`git checkout -b my-fixes`) so `main` stays as the pristine, bug-filled baseline you can reset to.
