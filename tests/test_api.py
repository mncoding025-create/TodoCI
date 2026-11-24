import json
import threading
import urllib.error
import urllib.request

import pytest

import server


@pytest.fixture()
def base(tmp_path, monkeypatch):
    monkeypatch.setenv("TODOCI_QUIET", "1")
    srv = server.create_server(0, str(tmp_path / "t.json"))
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    yield "http://127.0.0.1:%d" % srv.server_address[1]
    srv.shutdown()
    srv.server_close()


def call(base, method, path, body=None, raw=False):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            payload = r.read()
            return r.status, payload if raw else json.loads(payload)
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def test_health(base):
    code, body = call(base, "GET", "/health")
    assert code == 200 and body["status"] == "ok"


def test_index_page_served(base):
    code, html = call(base, "GET", "/", raw=True)
    assert code == 200 and b"TodoCI" in html


def test_crud_flow(base):
    code, t = call(base, "POST", "/api/tasks", {"title": "ส่งรายงาน", "due": "2026-12-31",
                                                "priority": "high", "tags": "uni,report"})
    assert code == 201 and t["id"] == 1 and t["tags"] == ["uni", "report"]
    assert call(base, "GET", "/api/tasks/1")[1]["title"] == "ส่งรายงาน"
    code, t = call(base, "PATCH", "/api/tasks/1", {"status": "done", "title": "แก้แล้ว"})
    assert code == 200 and t["status"] == "done" and t["title"] == "แก้แล้ว"
    assert call(base, "GET", "/api/stats")[1]["completion_rate"] == 100
    assert call(base, "DELETE", "/api/tasks/1")[0] == 200
    assert call(base, "GET", "/api/tasks")[1] == []


def test_filter_and_search_via_query(base):
    call(base, "POST", "/api/tasks", {"title": "อ่านหนังสือ", "priority": "low"})
    call(base, "POST", "/api/tasks", {"title": "ทำรายงาน", "priority": "high"})
    assert len(call(base, "GET", "/api/tasks?q=%E0%B8%A3%E0%B8%B2%E0%B8%A2%E0%B8%87%E0%B8%B2%E0%B8%99")[1]) == 1
    assert [t["title"] for t in call(base, "GET", "/api/tasks?sort=priority")[1]][0] == "ทำรายงาน"


def test_validation_errors_are_400(base):
    assert call(base, "POST", "/api/tasks", {"title": ""})[0] == 400
    assert call(base, "POST", "/api/tasks", {"title": "x", "due": "bad"})[0] == 400
    call(base, "POST", "/api/tasks", {"title": "ok"})
    assert call(base, "PATCH", "/api/tasks/1", {"status": "weird"})[0] == 400
    assert call(base, "GET", "/api/tasks?sort=zzz")[0] == 400


def test_not_found_is_404(base):
    assert call(base, "GET", "/api/tasks/42")[0] == 404
    assert call(base, "PATCH", "/api/tasks/42", {"title": "x"})[0] == 404
    assert call(base, "DELETE", "/api/tasks/42")[0] == 404
    assert call(base, "GET", "/nope")[0] == 404


def test_bad_json_is_400(base):
    req = urllib.request.Request(base + "/api/tasks", data=b"{oops", method="POST")
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(req)
    assert e.value.code == 400


def test_data_persisted_to_file(base, tmp_path):
    call(base, "POST", "/api/tasks", {"title": "เก็บลงไฟล์"})
    assert "เก็บลงไฟล์" in (tmp_path / "t.json").read_text(encoding="utf-8")


def test_clear_done(base):
    call(base, "POST", "/api/tasks", {"title": "a"})
    call(base, "PATCH", "/api/tasks/1", {"status": "done"})
    assert call(base, "POST", "/api/clear-done")[1] == {"removed": 1}
