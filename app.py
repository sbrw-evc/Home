"""NPM Dashboard: SPA с карточками сайтов из одного или нескольких Nginx Proxy Manager.

Источники:
  sqlite — локальная база NPM (database.sqlite), только чтение
  api    — удаленный NPM через его REST API (/api/tokens, /api/nginx/proxy-hosts)

Публичные эндпоинты:
  GET  /api/state      — текущее состояние (хосты, избранное, настройки поиска)
  GET  /api/events     — Server-Sent Events: состояние при каждом изменении
  GET  /health
Админские (заголовок X-Admin-Token, если задан ADMIN_PASSWORD):
  POST /api/login                 — проверка пароля
  GET  /api/config                — конфиг без паролей
  PUT  /api/config/general        — заголовок, поиск, показ выключенных
  PUT  /api/config/sources        — список источников NPM
  POST /api/sources/test          — проверить подключение к источнику
  POST /api/sites                 — добавить свой сайт
  PUT  /api/sites/<id>            — изменить свой сайт
  DELETE /api/sites/<id>          — удалить свой сайт
  POST /api/favorites             — {"key": ..., "on": true|false}
"""
import copy
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import ssl
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("PORT", "8088"))
CONFIG_PATH = os.environ.get("CONFIG", "/config/config.json")
DEFAULT_DB = os.environ.get("NPM_DB", "/npm/database.sqlite")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
SQLITE_POLL = float(os.environ.get("POLL_SECONDS", "2"))
API_POLL = float(os.environ.get("API_POLL_SECONDS", "30"))
STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

# OpenBao: логины и пароли удаленных NPM хранятся только там (KV v2)
BAO_ADDR = os.environ.get("BAO_ADDR", "").rstrip("/")
BAO_TOKEN = os.environ.get("BAO_TOKEN", "")
BAO_ROLE_ID = os.environ.get("BAO_ROLE_ID", "")
BAO_SECRET_ID = os.environ.get("BAO_SECRET_ID", "")
BAO_MOUNT = os.environ.get("BAO_KV_MOUNT", "secret").strip("/")
BAO_PREFIX = os.environ.get("BAO_PATH_PREFIX", "npm-dashboard/sources").strip("/")
BAO_ADMIN_PATH = os.environ.get("BAO_ADMIN_PATH", "npm-dashboard/admin").strip("/")
BAO_NAMESPACE =os.environ.get("BAO_NAMESPACE", "")
BAO_VERIFY = os.environ.get("BAO_SKIP_VERIFY", "false").lower() != "true"

config_lock = threading.RLock()
state_cond = threading.Condition()
wake = threading.Event()
public_state = {"version": None}


# ---------------------------------------------------------------- конфиг

def default_config():
    sources = []
    if os.path.exists(DEFAULT_DB):
        sources.append({"id": "local", "name": "Локальный NPM", "type": "sqlite",
                        "path": DEFAULT_DB, "enabled": True})
    return {
        "title": os.environ.get("TITLE", "Мои сервисы"),
        "show_disabled": os.environ.get("SHOW_DISABLED", "true").lower() == "true",
        "search": {"engine": "google", "custom": []},
        "sources": sources,
        "sites": [],
        "favorites": [],
    }


def load_config():
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg = json.load(f)
    except FileNotFoundError:
        cfg = default_config()
        save_config(cfg)
    base = default_config()
    for k, v in base.items():
        cfg.setdefault(k, v)
    return cfg


def save_config(cfg):
    os.makedirs(os.path.dirname(CONFIG_PATH) or ".", exist_ok=True)
    tmp = CONFIG_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    os.replace(tmp, CONFIG_PATH)


CONFIG = load_config()


def update_config(fn):
    with config_lock:
        cfg = copy.deepcopy(CONFIG)
        result = fn(cfg)
        save_config(cfg)
        CONFIG.clear()
        CONFIG.update(cfg)
    wake.set()
    return result


def is_http_url(s):
    return isinstance(s, str) and s.lower().startswith(("http://", "https://"))


def new_id():
    return secrets.token_hex(4)


# ---------------------------------------------------------------- OpenBao

class Bao:
    """Минимальный клиент OpenBao (совместим с Vault API): KV v2, вход по токену или AppRole."""

    def __init__(self):
        self.lock = threading.Lock()
        self.token = BAO_TOKEN
        self.cache = {}  # id источника -> (данные, время)

    @property
    def configured(self):
        return bool(BAO_ADDR and (BAO_TOKEN or (BAO_ROLE_ID and BAO_SECRET_ID)))

    def _req(self, method, path, data=None, token=True):
        headers = {"Accept": "application/json"}
        if token:
            headers["X-Vault-Token"] = self.token
        if BAO_NAMESPACE:
            headers["X-Vault-Namespace"] = BAO_NAMESPACE
        body = None
        if data is not None:
            body = json.dumps(data).encode()
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(f"{BAO_ADDR}/v1/{path}", data=body, headers=headers, method=method)
        ctx = None if BAO_VERIFY else ssl._create_unverified_context()
        try:
            with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
                raw = r.read()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            try:
                msg = "; ".join(json.loads(e.read().decode()).get("errors") or []) or e.reason
            except Exception:
                msg = e.reason
            err = RuntimeError(f"OpenBao HTTP {e.code}: {msg}")
            err.code = e.code
            raise err from None
        except urllib.error.URLError as e:
            raise RuntimeError(f"OpenBao недоступен: {e.reason}") from None

    def _login(self):
        res = self._req("POST", "auth/approle/login",
                        {"role_id": BAO_ROLE_ID, "secret_id": BAO_SECRET_ID}, token=False)
        self.token = res["auth"]["client_token"]

    def call(self, method, path, data=None):
        if not self.configured:
            raise RuntimeError("OpenBao не настроен (BAO_ADDR и BAO_TOKEN или BAO_ROLE_ID/BAO_SECRET_ID)")
        with self.lock:
            if not self.token:
                self._login()
            try:
                return self._req(method, path, data)
            except RuntimeError as e:
                # токен AppRole истек — входим заново
                if getattr(e, "code", None) == 403 and BAO_ROLE_ID:
                    self._login()
                    return self._req(method, path, data)
                raise

    def read(self, sid, max_age=60):
        c = self.cache.get(sid)
        if c and time.time() - c[1] < max_age:
            return c[0]
        res = self.call("GET", f"{BAO_MOUNT}/data/{BAO_PREFIX}/{sid}")
        data = (res or {}).get("data", {}).get("data") or {}
        self.cache[sid] = (data, time.time())
        return data

    def write(self, sid, data):
        self.call("POST", f"{BAO_MOUNT}/data/{BAO_PREFIX}/{sid}", {"data": data})
        self.cache[sid] = (data, time.time())

    def delete(self, sid):
        self.cache.pop(sid, None)
        self.call("DELETE", f"{BAO_MOUNT}/metadata/{BAO_PREFIX}/{sid}")

    def status(self):
        if not self.configured:
            return {"configured": False, "ok": False, "error": "не настроен"}
        try:
            self.call("GET", "auth/token/lookup-self")
            return {"configured": True, "ok": True, "error": "", "addr": BAO_ADDR}
        except Exception as e:
            return {"configured": True, "ok": False, "error": str(e), "addr": BAO_ADDR}


bao = Bao()
_admin_cache = {"pw": None, "at": 0}


def admin_password():
    """Пароль администратора: из ADMIN_PASSWORD или из OpenBao (ключ password по пути BAO_ADMIN_PATH)."""
    if ADMIN_PASSWORD or not bao.configured:
        return ADMIN_PASSWORD
    if time.time() - _admin_cache["at"] > 60:
        res = bao.call("GET", f"{BAO_MOUNT}/data/{BAO_ADMIN_PATH}")
        _admin_cache.update(pw=((res or {}).get("data", {}).get("data") or {}).get("password", ""), at=time.time())
    return _admin_cache["pw"]


# ---------------------------------------------------------------- источники

def fetch_sqlite(src):
    # meta намеренно не читаем: там могут быть ключи DNS-провайдеров
    con = sqlite3.connect(f"file:{src['path']}?mode=ro", uri=True, timeout=5)
    try:
        rows = con.execute(
            "SELECT id, domain_names, forward_scheme, forward_host, forward_port,"
            " enabled, certificate_id, access_list_id"
            " FROM proxy_host WHERE is_deleted = 0 ORDER BY id"
        ).fetchall()
    finally:
        con.close()
    return [{
        "id": r[0], "domain_names": json.loads(r[1] or "[]"), "forward_scheme": r[2],
        "forward_host": r[3], "forward_port": r[4], "enabled": r[5],
        "certificate_id": r[6], "access_list_id": r[7],
    } for r in rows]


_tokens = {}  # id источника -> (token, expires_ts, отпечаток учетных данных)


def _http_json(url, data=None, token=None, verify=True):
    headers = {"Accept": "application/json"}
    body = None
    if data is not None:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=body, headers=headers)
    ctx = None if verify else ssl._create_unverified_context()
    try:
        with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            msg = json.loads(e.read().decode()).get("error", {}).get("message") or e.reason
        except Exception:
            msg = e.reason
        err = RuntimeError(f"HTTP {e.code}: {msg}")
        err.code = e.code
        raise err from None
    except urllib.error.URLError as e:
        raise RuntimeError(f"нет соединения: {e.reason}") from None


def _api_token(src, force=False):
    # учетные данные: переданные явно (проверка подключения) или из OpenBao
    creds = src.get("_creds") or bao.read(src["id"])
    if not creds.get("email") or not creds.get("password"):
        raise RuntimeError("в OpenBao нет логина или пароля для этого источника")
    fp = hashlib.sha1(f"{src['url']}|{creds['email']}|{creds['password']}".encode()).hexdigest()
    cached = _tokens.get(src["id"])
    if cached and not force and cached[2] == fp and cached[1] - time.time() > 300:
        return cached[0]
    res = _http_json(src["url"].rstrip("/") + "/api/tokens",
                     {"identity": creds["email"], "secret": creds["password"]},
                     verify=src.get("verify_tls", True))
    if "token" not in res:
        raise RuntimeError("NPM не выдал токен (возможно, включена 2FA)")
    try:
        exp = datetime.fromisoformat(res["expires"].replace("Z", "+00:00")).timestamp()
    except Exception:
        exp = time.time() + 3600
    _tokens[src["id"]] = (res["token"], exp, fp)
    return res["token"]


def fetch_api(src):
    url = src["url"].rstrip("/") + "/api/nginx/proxy-hosts"
    verify = src.get("verify_tls", True)
    try:
        rows = _http_json(url, token=_api_token(src), verify=verify)
    except RuntimeError as e:
        if getattr(e, "code", None) != 401:
            raise
        rows = _http_json(url, token=_api_token(src, force=True), verify=verify)
    if not isinstance(rows, list):
        raise RuntimeError("неожиданный ответ API")
    return [r for r in rows if not r.get("is_deleted")]


def fetch_source(src):
    if src["type"] == "sqlite":
        return fetch_sqlite(src)
    if src["type"] == "api":
        return fetch_api(src)
    raise RuntimeError(f"неизвестный тип источника: {src['type']}")


def normalize(row, src):
    domains = row.get("domain_names") or []
    main = next((d for d in domains if not d.startswith("*")), domains[0] if domains else "")
    parts = main.split(".")
    cert = row.get("certificate_id")
    return {
        "key": f"{src['id']}:{row['id']}",
        "source": src["name"],
        "custom": False,
        "name": parts[0] if len(parts) > 2 else main,
        "domain": main,
        "domains": domains,
        "url": f"{'https' if cert else 'http'}://{main}",
        "target": f"{row.get('forward_scheme')}://{row.get('forward_host')}:{row.get('forward_port')}",
        "enabled": bool(row.get("enabled")),
        "ssl": bool(cert),
        "acl": bool(row.get("access_list_id")),
        "group": ".".join(parts[1:]) if len(parts) > 2 else main,
        "description": "",
        "icon": "",
    }


def custom_host(site):
    return {
        "key": f"custom:{site['id']}",
        "source": "Свои сайты",
        "custom": True,
        "id": site["id"],
        "name": site["name"],
        "domain": site["url"].split("://", 1)[-1].rstrip("/"),
        "domains": [],
        "url": site["url"],
        "target": "",
        "enabled": True,
        "ssl": site["url"].lower().startswith("https://"),
        "acl": False,
        "group": site.get("group") or "Свои сайты",
        "description": site.get("description", ""),
        "icon": site.get("icon", ""),
    }


# ---------------------------------------------------------------- опрос и состояние

_cache = {}  # id источника -> {"hosts": [...], "ok": bool, "error": str, "at": ts, "sig": ...}


def refresh_loop():
    while True:
        forced = wake.wait(timeout=1)
        wake.clear()
        with config_lock:
            cfg = copy.deepcopy(CONFIG)
        now = time.time()
        for src in cfg["sources"]:
            if not src.get("enabled", True):
                continue
            c = _cache.get(src["id"])
            sig = json.dumps(src, sort_keys=True)
            if src["type"] == "sqlite":
                try:
                    mtime = os.stat(src["path"]).st_mtime_ns
                except OSError:
                    mtime = None
                due = not c or c["sig"] != sig or c.get("mtime") != mtime or (not c["ok"] and now - c["at"] > SQLITE_POLL)
            else:
                mtime = None
                interval = float(src.get("poll_seconds") or API_POLL)
                due = forced or not c or c["sig"] != sig or now - c["at"] >= interval
            if not due:
                continue
            try:
                hosts = [normalize(r, src) for r in fetch_source(src)]
                _cache[src["id"]] = {"hosts": hosts, "ok": True, "error": "", "at": now, "sig": sig, "mtime": mtime}
            except Exception as e:
                old = c["hosts"] if c else []
                _cache[src["id"]] = {"hosts": old, "ok": False, "error": str(e), "at": now, "sig": sig, "mtime": None}
        publish(cfg)


def publish(cfg):
    hosts, sources = [], []
    for src in cfg["sources"]:
        c = _cache.get(src["id"])
        enabled = src.get("enabled", True)
        if enabled and c:
            hosts += [h for h in c["hosts"] if h["enabled"] or cfg["show_disabled"]]
        sources.append({
            "id": src["id"], "name": src["name"], "type": src["type"], "enabled": enabled,
            "ok": bool(c and c["ok"]) if enabled else None,
            "error": (c["error"] if c else "") if enabled else "",
            "count": len(c["hosts"]) if c and enabled else 0,
        })
    hosts += [custom_host(s) for s in cfg["sites"]]
    state = {
        "title": cfg["title"],
        "hosts": hosts,
        "favorites": cfg["favorites"],
        "search": cfg["search"],
        "sources": sources,
    }
    version = hashlib.sha1(json.dumps(state, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]
    with state_cond:
        if version != public_state.get("version"):
            state["version"] = version
            public_state.clear()
            public_state.update(state)
            state_cond.notify_all()


# ---------------------------------------------------------------- валидация ввода

def clean_site(data):
    name = str(data.get("name", "")).strip()[:100]
    url = str(data.get("url", "")).strip()[:2000]
    icon = str(data.get("icon", "")).strip()[:2000]
    if not name:
        raise ValueError("Укажите название")
    if not is_http_url(url):
        raise ValueError("Адрес должен начинаться с http:// или https://")
    if icon and not is_http_url(icon):
        raise ValueError("Адрес иконки должен начинаться с http:// или https://")
    return {
        "name": name, "url": url, "icon": icon,
        "group": str(data.get("group", "")).strip()[:100],
        "description": str(data.get("description", "")).strip()[:300],
    }


def clean_sources(items, old):
    """Возвращает (источники для config.json, {id: учетные данные для записи в OpenBao})."""
    out, creds, seen = [], {}, set()
    for d in items:
        t = d.get("type")
        src = {"id": d.get("id") or new_id(), "name": str(d.get("name", "")).strip()[:100] or "NPM",
               "type": t, "enabled": bool(d.get("enabled", True))}
        if src["id"] in seen:
            src["id"] = new_id()
        seen.add(src["id"])
        if t == "sqlite":
            src["path"] = str(d.get("path", "")).strip() or DEFAULT_DB
        elif t == "api":
            url = str(d.get("url", "")).strip().rstrip("/")
            if not is_http_url(url):
                raise ValueError(f"{src['name']}: адрес должен начинаться с http:// или https://")
            src.update(url=url, verify_tls=bool(d.get("verify_tls", True)))
            email, pw = str(d.get("email", "")).strip(), d.get("password") or ""
            if email or pw:
                # пустой пароль = оставить сохраненный в OpenBao
                saved = {} if pw else (bao.read(src["id"], max_age=0) if bao.configured else {})
                if not pw and not saved.get("password"):
                    raise ValueError(f"{src['name']}: укажите пароль")
                creds[src["id"]] = {"email": email or saved.get("email", ""), "password": pw or saved["password"]}
            try:
                ps = float(d.get("poll_seconds") or API_POLL)
            except (TypeError, ValueError):
                ps = API_POLL
            src["poll_seconds"] = max(5.0, ps)
        else:
            raise ValueError(f"{src['name']}: неизвестный тип источника")
        out.append(src)
    return out, creds


def public_config():
    with config_lock:
        cfg = copy.deepcopy(CONFIG)
    for s in cfg["sources"]:
        if s["type"] != "api":
            continue
        try:
            c = bao.read(s["id"])
            s["email"], s["has_password"], s["secret_error"] = c.get("email", ""), bool(c.get("password")), ""
        except Exception as e:
            s["email"], s["has_password"], s["secret_error"] = "", False, str(e)
    cfg["openbao"] = bao.status()
    cfg["openbao"]["path"] = f"{BAO_MOUNT}/{BAO_PREFIX}/<id>"
    return cfg


# ---------------------------------------------------------------- HTTP

class ApiError(Exception):
    def __init__(self, code, msg):
        super().__init__(msg)
        self.code = code


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def send(self, code, body, ctype="application/json; charset=utf-8"):
        if not isinstance(body, bytes):
            body = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n > 1_000_000:
            raise ApiError(413, "Слишком большой запрос")
        try:
            return json.loads(self.rfile.read(n) or b"{}")
        except json.JSONDecodeError:
            raise ApiError(400, "Некорректный JSON")

    def require_admin(self):
        try:
            pw = admin_password()
        except Exception as e:
            raise ApiError(503, f"Не удалось получить пароль администратора: {e}")
        if pw and not hmac.compare_digest(self.headers.get("X-Admin-Token", "").encode(), pw.encode()):
            raise ApiError(401, "Нужен пароль администратора")

    def handle_api(self, method):
        path = self.path.split("?")[0]
        try:
            if method == "GET":
                if path == "/api/state":
                    with state_cond:
                        return self.send(200, public_state)
                if path == "/api/events":
                    return self.events()
                if path == "/health":
                    return self.send(200, b"ok", "text/plain")
                if path == "/api/config":
                    self.require_admin()
                    return self.send(200, public_config())
                if path.startswith("/api/"):
                    raise ApiError(404, "Не найдено")
                with open(os.path.join(STATIC, "index.html"), "rb") as f:
                    return self.send(200, f.read(), "text/html; charset=utf-8")

            self.require_admin()
            data = self.body()

            if method == "POST" and path == "/api/login":
                return self.send(200, {"ok": True})

            if method == "PUT" and path == "/api/config/general":
                def fn(cfg):
                    if "title" in data:
                        cfg["title"] = str(data["title"]).strip()[:100] or "Мои сервисы"
                    if "show_disabled" in data:
                        cfg["show_disabled"] = bool(data["show_disabled"])
                    if "search_engine" in data:
                        cfg["search"]["engine"] = str(data["search_engine"])[:50]
                    if "custom_engines" in data:
                        engines = []
                        for e in data["custom_engines"]:
                            name, url = str(e.get("name", "")).strip()[:50], str(e.get("url", "")).strip()
                            if not name or not is_http_url(url) or "%s" not in url:
                                raise ValueError("Поисковик: нужно название и адрес http(s) с %s вместо запроса")
                            engines.append({"id": e.get("id") or new_id(), "name": name, "url": url})
                        cfg["search"]["custom"] = engines
                return self.send(200, update_config(fn) or {"ok": True})

            if method == "PUT" and path == "/api/config/sources":
                with config_lock:
                    old_ids = {s["id"] for s in CONFIG["sources"] if s["type"] == "api"}
                    sources, creds = clean_sources(data.get("sources", []), CONFIG["sources"])
                    # сначала секреты в OpenBao, потом конфиг — чтобы не остаться с источником без пароля
                    for sid, c in creds.items():
                        bao.write(sid, c)
                    update_config(lambda cfg: cfg.__setitem__("sources", sources))
                for sid in old_ids - {s["id"] for s in sources if s["type"] == "api"}:
                    try:
                        bao.delete(sid)
                    except Exception as e:
                        print(f"не удалось удалить секрет {sid} из OpenBao: {e}", flush=True)
                return self.send(200, public_config())

            if method == "POST" and path == "/api/sources/test":
                with config_lock:
                    srcs, creds = clean_sources([data], CONFIG["sources"])
                src = srcs[0]
                if src["id"] in creds:
                    src["_creds"] = creds[src["id"]]
                src["id"] = "test-" + src["id"]
                try:
                    n = len(fetch_source(src))
                    return self.send(200, {"ok": True, "count": n})
                except Exception as e:
                    return self.send(200, {"ok": False, "error": str(e)})
                finally:
                    _tokens.pop(src["id"], None)

            if method == "POST" and path == "/api/sites":
                site = clean_site(data)
                site["id"] = new_id()
                update_config(lambda cfg: cfg["sites"].append(site))
                return self.send(200, site)

            if path.startswith("/api/sites/") and method in ("PUT", "DELETE"):
                sid = path.rsplit("/", 1)[-1]
                site = clean_site(data) if method == "PUT" else None

                def fn(cfg):
                    idx = next((i for i, s in enumerate(cfg["sites"]) if s["id"] == sid), None)
                    if idx is None:
                        raise ApiError(404, "Сайт не найден")
                    if site:
                        cfg["sites"][idx] = {**site, "id": sid}
                    else:
                        cfg["sites"].pop(idx)
                        key = f"custom:{sid}"
                        cfg["favorites"] = [k for k in cfg["favorites"] if k != key]
                update_config(fn)
                return self.send(200, {"ok": True})

            if method == "POST" and path == "/api/favorites":
                key = str(data.get("key", ""))[:200]
                if not key:
                    raise ApiError(400, "Нет ключа")

                def fn(cfg):
                    favs = [k for k in cfg["favorites"] if k != key]
                    if data.get("on"):
                        favs.append(key)
                    cfg["favorites"] = favs
                update_config(fn)
                return self.send(200, {"ok": True})

            raise ApiError(404, "Не найдено")
        except ApiError as e:
            self.send(e.code, {"error": str(e)})
        except ValueError as e:
            self.send(400, {"error": str(e)})
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            self.send(500, {"error": str(e)})

    def do_GET(self):
        self.handle_api("GET")

    def do_POST(self):
        self.handle_api("POST")

    def do_PUT(self):
        self.handle_api("PUT")

    def do_DELETE(self):
        self.handle_api("DELETE")

    def events(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")  # чтобы nginx не буферизовал поток
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        self.close_connection = True
        last = None
        while True:
            with state_cond:
                state_cond.wait_for(lambda: public_state.get("version") not in (None, last), timeout=15)
                snap = dict(public_state) if public_state.get("version") != last else None
            try:
                if snap:
                    last = snap["version"]
                    self.wfile.write(f"event: state\ndata: {json.dumps(snap, ensure_ascii=False)}\n\n".encode())
                else:
                    self.wfile.write(b": ping\n\n")
                self.wfile.flush()
            except OSError:
                return

    def log_message(self, fmt, *args):
        pass


class Server(ThreadingHTTPServer):
    daemon_threads = True


if __name__ == "__main__":
    threading.Thread(target=refresh_loop, daemon=True).start()
    wake.set()
    print(f"NPM Dashboard on :{PORT}, config={CONFIG_PATH}, openbao={BAO_ADDR or 'off'}", flush=True)
    Server(("0.0.0.0", PORT), Handler).serve_forever()
