# Configuration

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `HOME_VERSION` | `latest` | Version of the `ghcr.io/sbrw-evc/home` image (used by `docker-compose.yml` only) |
| `HOME_PORT` | `8088` | Host port (used by `docker-compose.yml` only) |
| `NPM_DATA_DIR` | `./npm-data` | `data` directory of the local NPM (used by `docker-compose.yml` only) |
| `BAO_ADDR` | — | OpenBao address, e.g. `http://openbao:8200` |
| `BAO_TOKEN` | — | OpenBao token |
| `BAO_ROLE_ID`, `BAO_SECRET_ID` | — | AppRole login (instead of a token) |
| `BAO_KV_MOUNT` | `secret` | KV v2 mount path |
| `BAO_PATH_PREFIX` | `npm-dashboard/sources` | Where source credentials are stored |
| `BAO_ADMIN_PATH` | `npm-dashboard/admin` | Where the admin password is stored |
| `BAO_NAMESPACE` | — | OpenBao namespace |
| `BAO_SKIP_VERIFY` | `false` | Skip OpenBao TLS certificate verification |
| `ADMIN_PASSWORD` | — | Admin password; if set, it takes precedence over OpenBao and cannot be changed from the UI |
| `TITLE` | `Мои сервисы` | Page title on first start |
| `POLL_SECONDS` | `2` | How often to check the local database for changes |
| `API_POLL_SECONDS` | `30` | How often to poll remote NPM instances (can be set per source) |
| `ICON_TTL_HOURS` | `24` | How long found icons are cached |
| `CONFIG` | `/config/config.json` | Settings file inside the container |
| `NPM_DB` | `/npm/database.sqlite` | Default path to the local database |
| `PORT` | `8088` | Port inside the container |

## In-app settings

The **Settings** page (`#/settings`, requires the admin password):

- **General** — title, default search engine, showing disabled NPM hosts, custom search engines
  (URL with `%s` in place of the query, e.g. `https://github.com/search?q=%s`).
- **Security** — change the admin password, log out. See [[Security]].
- **NPM sources** — see [[NPM Sources|NPM-Sources]].
- **Custom sites** — list with editing.

## config.json

Stored in `./config/config.json` and written by the app. It contains no passwords.

```json
{
  "title": "My services",
  "show_disabled": true,
  "search": { "engine": "google", "custom": [{ "id": "gh", "name": "GitHub", "url": "https://github.com/search?q=%s" }] },
  "sources": [
    { "id": "local", "name": "Local NPM", "type": "sqlite", "path": "/npm/database.sqlite", "enabled": true },
    { "id": "a1b2c3d4", "name": "VPS", "type": "api", "url": "https://npm.example.com", "verify_tls": true, "poll_seconds": 30, "enabled": true }
  ],
  "sites": [{ "id": "e5f6", "name": "Router", "url": "http://192.168.0.1", "group": "Network", "description": "", "icon": "" }],
  "favorites": ["local:1", "custom:e5f6"]
}
```

Next to it is the `icons/` directory — the site icon cache. It is safe to delete; icons will be looked up again.

## Backup

Back up `./config` and the OpenBao data (`openbao/data` plus the unseal key).
