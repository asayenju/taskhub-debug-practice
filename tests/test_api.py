from datetime import datetime, timedelta

from conftest import signup


def make_task(client, auth, **fields):
    fields.setdefault("title", "Write report")
    resp = client.post("/tasks", json=fields, headers=auth)
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()


# ------------------------------------------------------------------- accounts


def test_register_and_login(client):
    assert signup(client)["Authorization"].startswith("Bearer ")


def test_usernames_are_case_insensitive(client):
    client.post("/register", json={"username": "Alice", "password": "password123"})
    resp = client.post("/register", json={"username": "alice", "password": "password123"})
    assert resp.status_code == 409


def test_login_works_with_any_username_casing(client):
    client.post("/register", json={"username": "Alice", "password": "password123"})
    resp = client.post("/login", json={"username": "ALICE", "password": "password123"})
    assert resp.status_code == 200


def test_login_does_not_reveal_whether_a_user_exists(client):
    client.post("/register", json={"username": "alice", "password": "password123"})
    wrong_pw = client.post("/login", json={"username": "alice", "password": "nope-nope"})
    no_user = client.post("/login", json={"username": "ghost", "password": "nope-nope"})
    assert wrong_pw.status_code == no_user.status_code == 401
    assert wrong_pw.get_json() == no_user.get_json()


def test_requests_without_a_token_are_rejected(client):
    assert client.get("/tasks").status_code == 401


def test_logout_invalidates_the_token(client, auth):
    assert client.post("/logout", headers=auth).status_code == 204
    assert client.get("/tasks", headers=auth).status_code == 401


# ---------------------------------------------------------------------- tasks


def test_create_and_fetch_task(client, auth):
    task = make_task(client, auth, title="Write the Report", priority=3)
    assert task["slug"] == "write-the-report"
    assert client.get(f"/tasks/{task['id']}", headers=auth).get_json()["priority"] == 3


def test_created_at_is_timezone_aware_utc(client, auth):
    task = make_task(client, auth)
    created = datetime.fromisoformat(task["created_at"])
    assert created.utcoffset() == timedelta(0)


def test_priority_must_be_an_integer(client, auth):
    for bad in ("high", 1.5, 9, -1):
        resp = client.post("/tasks", json={"title": "x", "priority": bad}, headers=auth)
        assert resp.status_code == 400, bad


def test_booleans_are_not_valid_priorities(client, auth):
    resp = client.post("/tasks", json={"title": "x", "priority": True}, headers=auth)
    assert resp.status_code == 400


def test_patch_only_changes_the_given_fields(client, auth):
    task = make_task(client, auth, title="Original", priority=4)
    resp = client.patch(f"/tasks/{task['id']}", json={"status": "doing"}, headers=auth)
    body = resp.get_json()
    assert (body["title"], body["priority"], body["status"]) == ("Original", 4, "doing")


def test_priority_can_be_patched_to_zero(client, auth):
    task = make_task(client, auth, priority=3)
    resp = client.patch(f"/tasks/{task['id']}", json={"priority": 0}, headers=auth)
    assert resp.get_json()["priority"] == 0


def test_list_is_paginated_newest_first(client, auth):
    for i in range(25):
        make_task(client, auth, title=f"task {i}")
    page1 = client.get("/tasks?page=1&per_page=10", headers=auth).get_json()
    assert page1["total"] == 25 and page1["total_pages"] == 3
    assert page1["items"][0]["title"] == "task 24"
    assert len(page1["items"]) == 10
    page3 = client.get("/tasks?page=3&per_page=10", headers=auth).get_json()
    assert len(page3["items"]) == 5


def test_filter_by_status_and_search(client, auth):
    make_task(client, auth, title="Buy milk")
    make_task(client, auth, title="Buy bread", status="done")
    make_task(client, auth, title="Call mom")
    assert client.get("/tasks?q=buy", headers=auth).get_json()["total"] == 2
    assert client.get("/tasks?q=buy&status=done", headers=auth).get_json()["total"] == 1


def test_search_input_cannot_escape_the_query(client):
    alice = signup(client, "alice")
    bob = signup(client, "bob")
    make_task(client, alice, title="alice's private task")
    resp = client.get("/tasks", query_string={"q": "%' OR 1=1 --"}, headers=bob)
    assert resp.status_code == 200
    assert resp.get_json()["total"] == 0


def test_users_cannot_read_or_edit_each_others_tasks(client):
    alice = signup(client, "alice")
    bob = signup(client, "bob")
    task = make_task(client, alice)
    assert client.get(f"/tasks/{task['id']}", headers=bob).status_code == 404
    assert client.patch(f"/tasks/{task['id']}", json={"title": "pwned"}, headers=bob).status_code == 404


def test_users_cannot_delete_each_others_tasks(client):
    alice = signup(client, "alice")
    bob = signup(client, "bob")
    task = make_task(client, alice)
    assert client.delete(f"/tasks/{task['id']}", headers=bob).status_code == 404
    assert client.get(f"/tasks/{task['id']}", headers=alice).status_code == 200


def test_owner_can_delete_their_task(client, auth):
    task = make_task(client, auth)
    assert client.delete(f"/tasks/{task['id']}", headers=auth).status_code == 204
    assert client.get(f"/tasks/{task['id']}", headers=auth).status_code == 404


# ---------------------------------------------------------------------- stats


def test_stats_count_by_status(client, auth):
    make_task(client, auth)
    make_task(client, auth, status="done")
    counts = client.get("/stats", headers=auth).get_json()["counts"]
    assert counts == {"todo": 1, "doing": 0, "done": 1}


def test_stats_are_per_user(client):
    alice = signup(client, "alice")
    bob = signup(client, "bob")
    make_task(client, alice)
    make_task(client, alice)
    assert client.get("/stats", headers=alice).get_json()["counts"]["todo"] == 2
    assert client.get("/stats", headers=bob).get_json()["counts"]["todo"] == 0


def test_stats_reflect_status_changes_immediately(client, auth):
    task = make_task(client, auth)
    assert client.get("/stats", headers=auth).get_json()["counts"]["todo"] == 1
    client.patch(f"/tasks/{task['id']}", json={"status": "done"}, headers=auth)
    counts = client.get("/stats", headers=auth).get_json()["counts"]
    assert counts["todo"] == 0 and counts["done"] == 1
