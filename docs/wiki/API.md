# API

All responses are JSON in UTF-8.

## Public

| Method and path | Description |
|---|---|
| `GET /api/state` | Current state: hosts, favorites, search settings, source status, version |
| `GET /api/events` | Server-Sent Events: a `state` event with the same payload on every change; a ping every 15 seconds |
| `GET /api/icon/<key>` | Site icon (`image/*`) or `404`. `key` is the host key from `/api/state` |
| `GET /health` | `ok <version>` |

Example state:

```json
{
  "title": "My services",
  "app_version": "1.0.0",
  "version": "3f2a9c1b0d4e",
  "hosts": [{
    "key": "local:1", "source": "Local NPM", "custom": false,
    "name": "proxmox", "domain": "proxmox.example.com", "domains": ["proxmox.example.com"],
    "url": "https://proxmox.example.com", "target": "https://192.168.0.200:8006",
    "enabled": true, "ssl": true, "acl": false, "group": "example.com", "description": "", "icon": ""
  }],
  "favorites": ["local:1"],
  "search": { "engine": "google", "custom": [] },
  "sources": [{ "id": "local", "name": "Local NPM", "type": "sqlite", "enabled": true, "ok": true, "error": "", "count": 19 }]
}
```

`version` is a hash of the state: it changes only when something changed.

## Admin password required

Header `X-Admin-Token: <URL-encoded password>` (`encodeURIComponent` in JS, `urllib.parse.quote` in Python).
Missing or wrong password — `401`.

| Method and path | Body | Description |
|---|---|---|
| `POST /api/login` | — | Check the password |
| `POST /api/admin/password` | `{"current", "new"}` | Change the password (`403` — wrong current password) |
| `GET /api/config` | — | Settings without passwords + OpenBao status |
| `PUT /api/config/general` | `{"title", "show_disabled", "search_engine", "custom_engines"}` | General settings |
| `PUT /api/config/sources` | `{"sources": [...]}` | Full list of sources; an empty `password` keeps the stored one |
| `POST /api/sources/test` | source | Connection test: `{"ok", "count"}` or `{"ok": false, "error"}` |
| `POST /api/sites` | `{"name", "url", "group", "description", "icon"}` | Add a custom site |
| `PUT /api/sites/<id>` | same | Update a custom site |
| `DELETE /api/sites/<id>` | — | Delete a custom site (and remove it from favorites) |
| `POST /api/favorites` | `{"key", "on"}` | Add to or remove from favorites |

Example:

```bash
curl -s -X POST http://localhost:8088/api/favorites \
  -H "X-Admin-Token: $(python3 -c 'import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))' 'password')" \
  -H 'Content-Type: application/json' -d '{"key":"local:1","on":true}'
```

Errors: `{"error": "message"}` with status `400`, `401`, `403`, `404` or `500`. Error messages are in Russian.
