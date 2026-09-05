#!/usr/bin/env python3

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import json
import os
import threading
from datetime import datetime, timezone

UPSTREAM = "http://127.0.0.1:1234"
LOGFILE = os.environ.get(
    "LMEVAL_LIVE_LOG",
    "/media/nowr/Data/Evals/qwen38-gsq/live/api-responses.jsonl",
)

lock = threading.Lock()
counter = 0


def append_record(record):
    data = (json.dumps(record, ensure_ascii=False) + "\n").encode("utf-8")

    with lock:
        fd = os.open(
            LOGFILE,
            os.O_WRONLY | os.O_CREAT | os.O_APPEND,
            0o644,
        )
        try:
            os.write(fd, data)
            os.fsync(fd)
        finally:
            os.close(fd)


class Handler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        if self.path == "/health":
            body = b'{"status":"ok"}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_error(404)

    def do_POST(self):
        global counter

        n = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(n)

        try:
            request_json = json.loads(body)
        except Exception:
            request_json = {"_raw": body.decode("utf-8", errors="replace")}

        headers = {
            "Content-Type": "application/json",
        }

        auth = self.headers.get("Authorization")
        if auth:
            headers["Authorization"] = auth

        req = Request(
            UPSTREAM + self.path,
            data=body,
            headers=headers,
            method="POST",
        )

        try:
            with urlopen(req, timeout=13000) as r:
                status = r.status
                raw = r.read()
        except HTTPError as e:
            status = e.code
            raw = e.read()
        except Exception as e:
            status = 502
            raw = json.dumps({
                "error": {
                    "message": repr(e),
                    "type": "proxy_error"
                }
            }).encode()

        try:
            response_json = json.loads(raw)
        except Exception:
            response_json = {
                "_raw": raw.decode("utf-8", errors="replace")
            }

        with lock:
            counter += 1
            seq = counter

        # 先持久化，再把结果返回给 lm-eval。
        append_record({
            "seq": seq,
            "time": datetime.now(timezone.utc).isoformat(),
            "path": self.path,
            "status": status,
            "request": request_json,
            "response": response_json,
        })

        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


if __name__ == "__main__":
    print("Logging proxy: http://127.0.0.1:1235")
    print("Upstream     :", UPSTREAM)
    print("Live log     :", LOGFILE)

    ThreadingHTTPServer(
        ("127.0.0.1", 1235),
        Handler,
    ).serve_forever()
