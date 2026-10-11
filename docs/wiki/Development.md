# Development

## Layout

```
app.py                       server: HTTP, source polling, SSE, OpenBao, icons (Python standard library only)
static/index.html            SPA: markup, styles and JS in one file, no build step or dependencies
Dockerfile                   image based on python:3.12-alpine
docker-compose.yml           runs Home
docker-compose.openbao.yml   attaches Home to the OpenBao network
openbao/                     OpenBao: compose, config, policy, setup.sh, unseal.sh
docs/wiki/                   this documentation
.github/workflows/           image build and release on tag
```

## Server (`app.py`)

- `ThreadingHTTPServer`, one thread per request; SSE clients wait on a `threading.Condition`.
- The background `refresh_loop` thread polls the sources and publishes the state (`publish`) with a `version` hash,
  so only real changes are broadcast.
- The config is written atomically (`config.json.tmp` → `os.replace`).
- A minimal OpenBao client: KV v2, token or AppRole with re-login on `403`.

## UI (`static/index.html`)

- Routes on `location.hash`: `#/`, `#/favorites`, `#/custom`, `#/group/<domain>`, `#/source/<name>`, `#/settings`.
- Cards are reused by host key and re-rendered only when they change.
- Framework-free components: select, checkbox, number input, password input, segmented control,
  modals, toasts, animated counters.

## Running locally

```bash
mkdir -p /tmp/home-config
CONFIG=/tmp/home-config/config.json NPM_DB=/path/to/database.sqlite ADMIN_PASSWORD=dev python3 app.py
# http://localhost:8088
```

Or with Docker: `docker compose up -d --build`.

## Releasing

1. Add release notes in `.github/release-notes/vX.Y.Z.md`.
2. Create and push a tag:

   ```bash
   git tag -a vX.Y.Z -m "Home vX.Y.Z" && git push origin vX.Y.Z
   ```

3. The **Release** workflow builds `ghcr.io/sbrw-evc/home` (amd64 + arm64) with tags `X.Y.Z`, `X.Y`, `latest`
   and creates a release with `home-X.Y.Z-deploy.tar.gz` and `SHA256SUMS`.
