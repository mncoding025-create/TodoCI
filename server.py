"""เว็บเซิร์ฟเวอร์ + REST API ของ TodoCI (ใช้เฉพาะไลบรารีมาตรฐาน)

รัน:   python3 server.py --port 3002
เปิด:  http://localhost:3002
"""
import argparse
import json
import os
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import storage
from todo import VERSION

HERE = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(HERE, "static")
TASK_PATH = re.compile(r"^/api/tasks/(\d+)$")


class TodoState:
    """ข้อมูลที่ใช้ร่วมกันทุก request (ล็อกกันเขียนชนกัน)"""

    def __init__(self, path: str):
        self.path = path
        self.lock = threading.Lock()
        self.todos = storage.load(path)

    def persist(self):
        storage.save(self.todos, self.path)


def make_handler(state: TodoState):
    class Handler(BaseHTTPRequestHandler):
        server_version = "TodoCI/" + VERSION

        # ---------- helpers ----------
        def log_message(self, fmt, *args):
            if os.environ.get("TODOCI_QUIET") != "1":
                super().log_message(fmt, *args)

        def _send(self, code, payload, ctype="application/json; charset=utf-8"):
            body = payload if isinstance(payload, bytes) else \
                json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def _error(self, code, message):
            self._send(code, {"error": message})

        def _body(self):
            length = int(self.headers.get("Content-Length") or 0)
            if length > 100_000:
                raise ValueError("ข้อมูลที่ส่งมาใหญ่เกินไป")
            raw = self.rfile.read(length) if length else b"{}"
            try:
                data = json.loads(raw.decode("utf-8") or "{}")
            except (ValueError, UnicodeDecodeError):
                raise ValueError("JSON ไม่ถูกต้อง")
            if not isinstance(data, dict):
                raise ValueError("ต้องส่งเป็น JSON object")
            return data

        def _run(self, fn):
            """รัน fn ภายใต้ล็อก แล้วแปลง error เป็น HTTP status"""
            try:
                with state.lock:
                    return fn()
            except KeyError as e:
                self._error(404, e.args[0] if e.args else "ไม่พบข้อมูล")
            except ValueError as e:
                self._error(400, str(e))

        # ---------- routes ----------
        def do_GET(self):
            url = urlparse(self.path)
            if url.path in ("/", "/index.html"):
                with open(os.path.join(STATIC_DIR, "index.html"), "rb") as f:
                    return self._send(200, f.read(), "text/html; charset=utf-8")
            if url.path == "/health":
                return self._send(200, {"status": "ok", "version": VERSION,
                                        "tasks": len(state.todos)})
            if url.path == "/api/stats":
                return self._run(lambda: self._send(200, state.todos.stats()))
            if url.path == "/api/tasks":
                qs = {k: v[0] for k, v in parse_qs(url.query).items()}
                return self._run(lambda: self._send(200, [
                    vars(t) for t in state.todos.list(
                        status=qs.get("status"), priority=qs.get("priority"),
                        tag=qs.get("tag"), q=qs.get("q"), sort=qs.get("sort", "id"))]))
            m = TASK_PATH.match(url.path)
            if m:
                return self._run(lambda: self._send(200, vars(state.todos.get(int(m.group(1))))))
            self._error(404, "ไม่พบหน้านี้")

        def do_POST(self):
            path = urlparse(self.path).path
            if path == "/api/tasks":
                def create():
                    d = self._body()
                    t = state.todos.add(d.get("title"), d.get("due"),
                                        d.get("priority", "medium"), d.get("tags"))
                    state.persist()
                    self._send(201, vars(t))
                return self._run(create)
            if path == "/api/clear-done":
                def clear():
                    n = state.todos.clear_done()
                    state.persist()
                    self._send(200, {"removed": n})
                return self._run(clear)
            self._error(404, "ไม่พบหน้านี้")

        def do_PATCH(self):
            m = TASK_PATH.match(urlparse(self.path).path)
            if not m:
                return self._error(404, "ไม่พบหน้านี้")
            task_id = int(m.group(1))

            def update():
                d = self._body()
                tl = state.todos
                tl.get(task_id)  # 404 ก่อนถ้าไม่มี
                if any(k in d for k in ("title", "due", "priority", "tags")):
                    tl.edit(task_id, d.get("title"), d.get("due"),
                            d.get("priority"), d.get("tags"))
                if "status" in d:
                    tl.set_status(task_id, d["status"])
                state.persist()
                self._send(200, vars(tl.get(task_id)))
            return self._run(update)

        def do_DELETE(self):
            m = TASK_PATH.match(urlparse(self.path).path)
            if not m:
                return self._error(404, "ไม่พบหน้านี้")

            def remove():
                state.todos.delete(int(m.group(1)))
                state.persist()
                self._send(200, {"deleted": int(m.group(1))})
            return self._run(remove)

    return Handler


def create_server(port: int = 0, data_file: str = "tasks.json",
                  host: str = "127.0.0.1") -> ThreadingHTTPServer:
    """สร้างเซิร์ฟเวอร์ (port=0 = ให้ระบบเลือกพอร์ตว่างให้ ใช้ในเทสต์)"""
    state = TodoState(data_file)
    return ThreadingHTTPServer((host, port), make_handler(state))


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description="TodoCI web server")
    p.add_argument("--port", type=int, default=int(os.environ.get("PORT", 3002)))
    p.add_argument("--host", default=os.environ.get("HOST", "0.0.0.0"))
    p.add_argument("--file", default=os.environ.get("TODO_FILE", "tasks.json"))
    args = p.parse_args(argv)
    srv = create_server(args.port, args.file, args.host)
    print("TodoCI %s รันที่ http://localhost:%d  (ข้อมูล: %s)" % (VERSION, args.port, args.file),
          flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nหยุดเซิร์ฟเวอร์")
    finally:
        srv.server_close()


if __name__ == "__main__":
    main()
