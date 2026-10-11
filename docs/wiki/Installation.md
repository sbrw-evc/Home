# Installation

Requirements: Docker 24+ with Compose v2. The image is built for `linux/amd64` and `linux/arm64`.

## From a release (recommended)

```bash
curl -L https://github.com/sbrw-evc/Home/releases/download/v1.0.0/home-1.0.0-deploy.tar.gz | tar xz
cd home-1.0.0
cp .env.example .env
```

Set in `.env`:

- `NPM_DATA_DIR` — path to the `data` directory of your local Nginx Proxy Manager, the one NPM mounts as `/data`
  (for example `/data/compose/1/data`). If there is no local NPM, leave it as is and add sources in the settings.
- `HOME_PORT` — host port for the page (`8088` by default).

### Option A: OpenBao next to Home

```bash
./openbao/setup.sh
docker compose -f docker-compose.yml -f docker-compose.openbao.yml up -d
```

`setup.sh` starts OpenBao, initializes and unseals it, creates the policy and AppRole, writes `BAO_*` into `.env`
and generates an admin password. See [[OpenBao]].

> **Important:** store the contents of `/root/openbao-init.json` (unseal key and root token) in a password manager and delete the file from the server.

### Option B: your own OpenBao

Fill in `BAO_ADDR` and `BAO_ROLE_ID`/`BAO_SECRET_ID` (or `BAO_TOKEN`) in `.env`, set up the policy as described in [[OpenBao]], then run:

```bash
docker compose up -d
```

### Option C: without OpenBao

Set `ADMIN_PASSWORD` in `.env` and run `docker compose up -d`. The local NPM, custom sites, favorites and search work;
**remote NPM instances cannot be added**, because their passwords are stored only in OpenBao.

## First login

1. Open `http://<host>:8088`.
2. If the local NPM database is mounted, the "Локальный NPM" (local NPM) source is added automatically.
3. Open **Settings** (`#/settings`) — it asks for the admin password.
   When installed with `setup.sh`, read it like this:

   ```bash
   docker exec -it -e BAO_ADDR=http://127.0.0.1:8200 openbao sh -c 'bao login && bao kv get -field=password secret/npm-dashboard/admin'
   ```

   Then change it in the **Security** card.

## From source

```bash
git clone https://github.com/sbrw-evc/Home.git && cd Home
cp .env.example .env
docker compose up -d --build
```

## Behind Nginx Proxy Manager

Create an NPM proxy host pointing to `http://<host>:8088`. The `/api/events` stream works through NPM without extra
configuration: the app sends `X-Accel-Buffering: no`, which turns off nginx buffering.

## Upgrading

```bash
sed -i 's/^HOME_VERSION=.*/HOME_VERSION=1.0.0/' .env   # the version you want
docker compose pull && docker compose up -d
```

Settings, custom sites, favorites and the icon cache live in `./config` and survive upgrades.
Logins and passwords live in OpenBao.
