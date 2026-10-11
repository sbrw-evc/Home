# NPM Sources

Home shows proxy hosts (`Proxy Hosts`) from one or more Nginx Proxy Manager instances. Sources are configured in
**Settings → NPM sources**; the **Check** button tests the connection without saving.

## Local database (SQLite)

By default NPM keeps its data in `data/database.sqlite`. Mount the `data` directory into the Home container read-only:

```yaml
volumes:
  - /path/to/npm/data:/npm:ro
```

- The file is opened read-only (`mode=ro`); Home never changes anything in NPM.
- Changes are picked up by the file modification time (every `POLL_SECONDS`).
- Only domains, forward address, status, certificate and access list are read from the `proxy_host` table.
  The `meta` field — where NPM stores DNS provider keys — is **not read**.
- SQLite only. Connect NPM instances that use MySQL/MariaDB as remote sources via the API.

## Remote NPM (API)

For NPM on another server or on the internet:

| Field | Description |
|---|---|
| NPM address | Admin UI address, e.g. `https://npm.example.com` or `http://10.0.0.5:81` |
| Login, password | NPM account. Stored **only in OpenBao**, see [[OpenBao]] |
| Poll, sec | How often to fetch the host list (minimum 5) |
| Verify TLS | Uncheck for a self-signed certificate |

Home gets a token via `POST /api/tokens` and reads `GET /api/nginx/proxy-hosts`. The token is cached and refreshed
automatically. A dedicated NPM account that can only view proxy hosts is recommended.

> If NPM does not issue a token for the login and password (for example, the account has two-factor authentication enabled),
> the source shows an error — use a dedicated account without 2FA.

An empty password field on save means "keep the stored one". When a source is deleted, its secret is removed from OpenBao.

## What a card shows

| NPM field | On the card |
|---|---|
| First domain without `*` | Name (subdomain) and link |
| Other domains | Extra lines |
| `forward_scheme://forward_host:forward_port` | Forward address |
| Certificate | HTTPS or HTTP; the link uses `https://` if a certificate is set |
| Access list | ACL badge |
| Disabled | Card is semi-transparent (can be hidden in settings) |

Menu groups are the parent domain (`got-it.example.com` for `ldap.got-it.example.com`).
With several sources, the menu gets a "Sources" section and cards get a source badge.
