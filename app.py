"""NPM Dashboard: SPA с карточками сайтов из базы Nginx Proxy Manager (только чтение).

GET /              — SPA (static/index.html)
GET /api/hosts     — список хостов в JSON
GET /api/events    — Server-Sent Events: присылает список при каждом изменении базы
"""
import hashlib
import json
import os
import sqlite3
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DB_PATH = os.environ.get("NPM_DB", "/npm/database.sqlite")
PORT = int(os.environ.get("PORT", "8088"))
TITLE = os.environ.get("TITLE", "Мои сервисы")
SHOW_DISABLED = os.environ.get("SHOW_DISABLED", "true").lower() == "true"
POLL_SECONDS = float(os.environ.get("POLL_SECONDS", "2"))
STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


def load_hosts():
    # meta намеренно не читаем: там могут быть ключи DNS-провайдеров
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=5)
    try:
        rows = con.execute(
            "SELECT id, domain_names, forward_scheme, forward_host, forward_port,"
            " enabled, certificate_id, access_list_id"
            " FROM proxy_host WHERE is_deleted = 0 ORDER BY id"
        ).fetchall()
    finally:
        con.close()

    hosts = []
    for id_, domains, scheme, fhost, fport, enabled, cert, acl in rows:
        if not enabled and not SHOW_DISABLED:
            continue
        domains = json.loads(domains or "[]")
        # для ссылки берем первый домен без wildcard
        main = next((d for d in domains if not d.startswith("*")), domains[0] if domains else "")
        parts = main.split(".")
        hosts.append({
            "id": id_,
            "name": parts[0] if len(parts) > 2 else main,
            "domain": main,
            "domains": domains,
            "url": f"{'https' if cert else 'http'}://{main}",
            "target": f"{scheme}://{fhost}:{fport}",
            "enabled": bool(enabled),
            "ssl": bool(cert),
            "acl": bool(acl),
            "group": ".".join(parts[1:]) if len(parts) > 2 else main,
        })
    return hosts


def snapshot():
    hosts = load_hosts()
    payload = {"title": TITLE, "hosts": hosts}
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    payload["version"] = hashlib.sha1(body.encode()).hexdigest()[:12]
    payload["updated"] = int(time.time())
    return payload


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]
        try:
            if path == "/api/hosts":
                self.send(200, json.dumps(snapshot(), ensure_ascii=False).encode(), "application/json; charset=utf-8")
            elif path == "/api/events":
                self.events()
            elif path == "/health":
                self.send(200, b"ok", "text/plain")
            else:
                # SPA: любой другой путь отдает index.html
                with open(os.path.join(STATIC, "index.html"), "rb") as f:
                    self.send(200, f.read(), "text/html; charset=utf-8")
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as ex:
            self.send(500, json.dumps({"error": str(ex)}).encode(), "application/json")

    def events(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")  # чтобы nginx не буферизовал поток
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        self.close_connection = True

        last_mtime, last_version, last_ping = None, None, time.time()
        while True:
            try:
                mtime = os.stat(DB_PATH).st_mtime_ns
                if mtime != last_mtime:
                    last_mtime = mtime
                    snap = snapshot()
                    if snap["version"] != last_version:
                        last_version = snap["version"]
                        data = json.dumps(snap, ensure_ascii=False)
                        self.wfile.write(f"event: hosts\ndata: {data}\n\n".encode())
                        self.wfile.flush()
                if time.time() - last_ping > 15:
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
                    last_ping = time.time()
            except (BrokenPipeError, ConnectionResetError):
                return
            except Exception as ex:
                try:
                    self.wfile.write(f"event: failure\ndata: {json.dumps(str(ex))}\n\n".encode())
                    self.wfile.flush()
                except OSError:
                    return
                last_mtime = None
            time.sleep(POLL_SECONDS)

    def log_message(self, fmt, *args):
        pass


class Server(ThreadingHTTPServer):
    daemon_threads = True


if __name__ == "__main__":
    print(f"NPM Dashboard on :{PORT}, db={DB_PATH}", flush=True)
    Server(("0.0.0.0", PORT), Handler).serve_forever()
