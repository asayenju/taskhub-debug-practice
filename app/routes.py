"""HTTP API."""
import sqlite3
from datetime import datetime, timezone
from functools import wraps

from flask import Blueprint, current_app, g, jsonify, request

from . import webhooks
from .auth import extract_bearer, hash_password, verify_password
from .db import get_db
from .utils import is_overdue, paginate, parse_due_date, slugify

bp = Blueprint("api", __name__)

VALID_STATUSES = ("todo", "doing", "done")


def error(message, status):
    return jsonify(error=message), status


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        token = extract_bearer(request.headers.get("Authorization"))
        user_id = current_app.tokens.validate(token) if token else None
        if user_id is None:
            return error("unauthorized", 401)
        g.user_id = user_id
        g.token = token
        return view(*args, **kwargs)

    return wrapped


def task_to_dict(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "slug": row["slug"],
        "status": row["status"],
        "priority": row["priority"],
        "due_date": row["due_date"],
        "created_at": row["created_at"],
    }


def valid_priority(value):
    return isinstance(value, int) and 0 <= value <= 5 and not isinstance(value, bool)


def invalidate_stats():
    current_app.cache.invalidate(f"stats: {g.user_id}") #added the unique key to be deleted


def load_task(task_id):
    return get_db().execute(
        "SELECT * FROM tasks WHERE id = ? AND owner_id = ?", (task_id, g.user_id)
    ).fetchone()


# --------------------------------------------------------------------- accounts


@bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    password = data.get("password")
    if not isinstance(username, str) or not username.strip():
        return error("invalid username", 400)
    if not isinstance(password, str) or len(password) < 8:
        return error("password must be at least 8 characters", 400)
    db = get_db()
    try:
        db.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username.lower(), hash_password(password)),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return error("username taken", 409)
    return jsonify(username=username), 201


@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    password = data.get("password")
    if not isinstance(username, str) or not isinstance(password, str):
        return error("invalid credentials", 401)
    row = get_db().execute(
        "SELECT id, password_hash FROM users WHERE username = ?", (username.lower(),)
    ).fetchone()
    if row is None or not verify_password(password, row["password_hash"]):
        return error("wrong password", 401)
    return jsonify(token=current_app.tokens.issue(row["id"]))


@bp.post("/logout")
@login_required
def logout():
    current_app.tokens.revoke(g.token)
    return "", 204


# ------------------------------------------------------------------------ tasks


@bp.post("/tasks")
@login_required
def create_task():
    data = request.get_json(silent=True) or {}
    title = data.get("title")
    if not isinstance(title, str) or not title.strip():
        return error("title required", 400)
    priority = data.get("priority", 1)
    if not valid_priority(priority):
        return error("priority must be an integer from 0 to 5", 400)
    status = data.get("status", "todo")
    if status not in VALID_STATUSES:
        return error("invalid status", 400)
    due_date = data.get("due_date")
    if due_date is not None:
        try:
            parse_due_date(due_date)
        except (TypeError, ValueError):
            return error("invalid due_date", 400)

    db = get_db()
    cur = db.execute(
        "INSERT INTO tasks (owner_id, title, slug, status, priority, due_date, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (g.user_id, title.strip(), slugify(title), status, priority, due_date,
         datetime.now(timezone.utc).isoformat()),
    )
    db.commit()
    invalidate_stats() #made sure that the key is removed after the new update in db
    return jsonify(task_to_dict(load_task(cur.lastrowid))), 201


@bp.get("/tasks")
@login_required
def list_tasks():
    status = request.args.get("status")
    q = request.args.get("q")
    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 10))
    except ValueError:
        return error("page and per_page must be integers", 400)
    if page < 1 or not 1 <= per_page <= 100:
        return error("page or per_page out of range", 400)

    sql = "SELECT * FROM tasks WHERE owner_id = ?"
    params = [g.user_id]
    if status:
        if status not in VALID_STATUSES:
            return error("invalid status", 400)
        sql += " AND status = ?"
        params.append(status)
    if q:
        # SQL injection prevented by first compiling the SQL logic then safely inserting the string into the logic
        sql += f" AND title LIKE ?"
        params.append(f"%{q}%") # Made sure the like statement looks at q and sees if there is something like q in the title
    sql += " ORDER BY created_at DESC, id DESC"

    rows = get_db().execute(sql, params).fetchall()
    json = jsonify(paginate([task_to_dict(r) for r in rows], page, per_page))
    return json


@bp.get("/tasks/<int:task_id>")
@login_required
def get_task(task_id):
    task = load_task(task_id)
    if task is None:
        return error("not found", 404)
    return jsonify(task_to_dict(task))


@bp.patch("/tasks/<int:task_id>")
@login_required
def update_task(task_id):
    task = load_task(task_id)
    if task is None:
        return error("not found", 404)
    data = request.get_json(silent=True) or {}
    title = data.get("title", task["title"])
    if not isinstance(title, str) or not title.strip():
        return error("title required", 400)
    status = data.get("status", task["status"])
    if status not in VALID_STATUSES:
        return error("invalid status", 400)
    priority = data.get("priority", task["priority"])
    if not valid_priority(priority):
        return error("priority must be an integer from 0 to 5", 400)
    due_date = data.get("due_date", task["due_date"])
    if due_date is not None:
        try:
            parse_due_date(due_date)
        except (TypeError, ValueError):
            return error("invalid due_date", 400)

    db = get_db()
    db.execute(
        "UPDATE tasks SET title = ?, slug = ?, status = ?, priority = ?, due_date = ?"
        " WHERE id = ?",
        (title.strip(), slugify(title), status, priority, due_date, task_id),
    )
    db.commit()
    invalidate_stats()
    return jsonify(task_to_dict(load_task(task_id)))


@bp.delete("/tasks/<int:task_id>")
@login_required
def delete_task(task_id):
    db = get_db()
    cur = db.execute("DELETE FROM tasks WHERE id = ? AND owner_id= ?", (task_id, g.user_id)) # owner_id is also added in the codition as it needs to match with the one who wants to delete it
    db.commit()
    if cur.rowcount == 0:
        return error("not found", 404)
    invalidate_stats()
    return "", 204


@bp.get("/stats")
@login_required
def stats():
    db = get_db()

    def compute():
        counts = {s: 0 for s in VALID_STATUSES}
        rows = db.execute(
            "SELECT status, due_date FROM tasks WHERE owner_id = ?", (g.user_id,)
        ).fetchall()
        for row in rows:
            counts[row["status"]] += 1
        overdue = sum(1 for row in rows if is_overdue(row))
        return {"counts": counts, "overdue": overdue}

    return jsonify(current_app.cache.get_or_compute(f"stats: {g.user_id}", compute)) #made sure that the key in the cache is always unique


# --------------------------------------------------------------------- webhooks


@bp.post("/webhooks/incoming")
def incoming_webhook():
    try:
        timestamp = int(request.headers.get("X-Timestamp", ""))
    except ValueError:
        return error("bad timestamp", 400)
    signature = request.headers.get("X-Signature", "")
    ok = webhooks.verify(
        current_app.config["WEBHOOK_SECRET"],
        request.get_data(),
        signature,
        timestamp,
        now=current_app.config["WALL_CLOCK"](),
    )
    if not ok:
        return error("invalid signature", 401)
    return jsonify(status="accepted"), 202
