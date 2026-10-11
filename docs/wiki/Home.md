# Home

**Home** is a start page for a homelab. It turns every site configured in
[Nginx Proxy Manager](https://nginxproxymanager.com/) into a card, adds your own sites, favorites and a search bar,
and updates live without reloading the page.

## Contents

| Page | About |
|---|---|
| [[Installation]] | Installing from a release or from source, first login, upgrading |
| [[Configuration]] | Environment variables, `config.json`, in-app settings |
| [[NPM Sources\|NPM-Sources]] | Local SQLite database and remote NPM instances via API |
| [[OpenBao]] | Storing logins and passwords, AppRole, unsealing |
| [[Security]] | Admin password, what is visible without login, recommendations |
| [[Features]] | Search, favorites, custom sites, icons, keyboard shortcuts |
| [[API]] | REST API and the SSE event stream |
| [[Troubleshooting]] | Common issues and diagnostics |
| [[Development]] | Code structure and running locally |

## How it works

```
 Nginx Proxy Manager ──(database.sqlite, read-only)──────┐
 remote NPM ─────────────(REST API, login from OpenBao)──┤
                                                          ▼
                         Home (Python, single process) ──SSE──► browser (SPA)
                           │        │
            config/config.json   OpenBao (KV v2)
   (custom sites, favorites,    (NPM logins/passwords,
    settings, icon cache)        admin password)
```

- The server polls its sources: the local database on file change (every 2 seconds), remote NPM instances every 30 seconds.
- When the list changes, the new state is pushed to every open page via Server-Sent Events.
- The page re-renders only the cards that changed and highlights them.

## Quick start

```bash
curl -L https://github.com/sbrw-evc/Home/releases/download/v1.0.0/home-1.0.0-deploy.tar.gz | tar xz
cd home-1.0.0 && cp .env.example .env
./openbao/setup.sh
docker compose -f docker-compose.yml -f docker-compose.openbao.yml up -d
```

The page opens at `http://<host>:8088`. See [[Installation]] for details.

> The web interface is in Russian.
