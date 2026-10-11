# Home

A start page for your homelab: cards for every site in [Nginx Proxy Manager](https://nginxproxymanager.com/),
your own sites, favorites and a search bar. Updates live, without reloading the page.

[Releases](https://github.com/sbrw-evc/Home/releases) · [Image](https://github.com/sbrw-evc/Home/pkgs/container/home) · [Wiki](https://github.com/sbrw-evc/Home/wiki)

## Features

- **Sites from NPM** — a local `database.sqlite` (read-only) and/or remote NPM instances via the REST API.
- **Live updates** over Server-Sent Events: NPM changes show up within seconds, changed cards are highlighted.
- **Search** focused on page load, with a choice of search engine: typing filters cards, `Enter` searches the web.
- **Custom sites and favorites** — stored on the server, the same on every device.
- **Site icons** are resolved on the server: `<link rel="icon">`, web manifest, `/favicon.ico`, including via the NPM backend.
- **Secrets only in [OpenBao](https://openbao.org/)**: remote NPM logins and passwords and the admin password.
- Settings, connection checks and password change — all in the UI.
- No dependencies: Python 3 stdlib + vanilla JS. Image for `linux/amd64` and `linux/arm64`.

The web interface is in Russian.

## Quick start

```bash
curl -L https://github.com/sbrw-evc/Home/releases/download/v1.0.0/home-1.0.0-deploy.tar.gz | tar xz
cd home-1.0.0
cp .env.example .env          # NPM_DATA_DIR — the data directory of your local NPM
./openbao/setup.sh            # OpenBao next to Home: keys in /root/openbao-init.json, AppRole in .env
docker compose -f docker-compose.yml -f docker-compose.openbao.yml up -d
```

The page is at `http://<host>:8088`, settings at `#/settings`.

> Store `/root/openbao-init.json` (unseal key and root token) in a password manager and delete it from the server.
> After an OpenBao restart, unseal it: `./openbao/unseal.sh`.

Without OpenBao: set `ADMIN_PASSWORD` in `.env` and run `docker compose up -d` — everything except remote NPM instances works.

## Documentation

| | |
|---|---|
| [Installation](https://github.com/sbrw-evc/Home/wiki/Installation) | Install options, first login, upgrading |
| [Configuration](https://github.com/sbrw-evc/Home/wiki/Configuration) | Environment variables and `config.json` |
| [NPM Sources](https://github.com/sbrw-evc/Home/wiki/NPM-Sources) | Local database and remote NPM instances |
| [OpenBao](https://github.com/sbrw-evc/Home/wiki/OpenBao) | Secret storage, policy, AppRole |
| [Security](https://github.com/sbrw-evc/Home/wiki/Security) | Admin password and recommendations |
| [API](https://github.com/sbrw-evc/Home/wiki/API) | REST API and SSE |
| [Troubleshooting](https://github.com/sbrw-evc/Home/wiki/Troubleshooting) | Diagnostics |

Wiki sources live in [`docs/wiki`](docs/wiki).
