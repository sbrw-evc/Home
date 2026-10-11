# OpenBao

Logins and passwords of remote NPM instances and the Home admin password are stored only in [OpenBao](https://openbao.org/),
an open-source fork of HashiCorp Vault. They are never written to `config.json`.

| What | Path (KV v2) | Keys |
|---|---|---|
| Remote NPM credentials | `secret/npm-dashboard/sources/<source id>` | `email`, `password` |
| Admin password | `secret/npm-dashboard/admin` | `password` |

Home creates and deletes source secrets itself when you save the settings.

## OpenBao next to Home

The `openbao/` directory contains a compose file (file storage, port bound to `127.0.0.1:8200` only) and scripts.

```bash
./openbao/setup.sh
docker compose -f docker-compose.yml -f docker-compose.openbao.yml up -d
```

`setup.sh` (safe to run again):

1. creates the `openbao` docker network and starts the container;
2. initializes OpenBao (1 unseal key) and saves the key and root token to `/root/openbao-init.json` with mode `600`;
3. unseals it;
4. enables KV v2 at `secret/`, creates the `npm-dashboard` policy and AppRole;
5. writes `BAO_ADDR`, `BAO_ROLE_ID`, `BAO_SECRET_ID` into `.env` (other lines are left untouched);
6. generates an admin password if there is none yet.

> **Store `/root/openbao-init.json` in a password manager and delete it from the server.** Without the unseal key the data cannot be recovered.

### After a restart

OpenBao is sealed after a restart. While it is sealed, the local NPM still shows on the page, but remote NPM instances and settings do not work.

```bash
./openbao/unseal.sh     # takes the key from /root/openbao-init.json or asks for it
```

## Your own OpenBao

Policy:

```hcl
path "secret/data/npm-dashboard/*"     { capabilities = ["create", "read", "update"] }
path "secret/metadata/npm-dashboard/*" { capabilities = ["delete"] }
path "auth/token/lookup-self"          { capabilities = ["read"] }
```

AppRole:

```bash
bao policy write npm-dashboard npm-dashboard.hcl
bao auth enable approle
bao write auth/approle/role/npm-dashboard token_policies=npm-dashboard token_ttl=1h token_max_ttl=24h
bao read auth/approle/role/npm-dashboard/role-id
bao write -f auth/approle/role/npm-dashboard/secret-id
```

Set `BAO_ADDR`, `BAO_ROLE_ID`, `BAO_SECRET_ID` in `.env`. If OpenBao is in another docker network or on another host,
use its address; for a self-signed certificate set `BAO_SKIP_VERIFY=true`.

Home logs in again via AppRole when its token expires. The connection status is shown in **Settings → NPM sources**.
