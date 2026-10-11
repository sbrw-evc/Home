# Troubleshooting

## Diagnostics

```bash
docker logs home                         # version, OpenBao address, errors
curl -s localhost:8088/health            # ok <version>
curl -s localhost:8088/api/state | python3 -m json.tool | grep -A6 '"sources"'
```

The status and connection error of each source are shown in **Settings → NPM sources**; source errors also show in the status dot at the bottom of the menu.

## Common issues

**No cards from the local NPM.**
Check `NPM_DATA_DIR` in `.env`: the container must have `/npm/database.sqlite`
(`docker exec home ls -l /npm`). Connect NPM instances that use MySQL/MariaDB via the API.

**Remote NPM: `HTTP 400: Invalid email or password`.**
Wrong login or password. The password is stored in OpenBao — enter it again and save.

**Remote NPM: `нет соединения` (no connection), `certificate verify failed`.**
The address is not reachable from the container, or the certificate is self-signed — uncheck "Verify TLS certificate".

**`OpenBao недоступен` (unavailable), `OpenBao HTTP 503: Vault is sealed`.**
OpenBao is sealed after a restart: `./openbao/unseal.sh`.

**`OpenBao не настроен` (not configured).**
`BAO_ADDR` and `BAO_TOKEN` or `BAO_ROLE_ID`/`BAO_SECRET_ID` are not set. Remote NPM instances cannot be added without OpenBao.

**Settings do not open: "Нужен пароль администратора" (admin password required).**
Get the password: `bao kv get -field=password secret/npm-dashboard/admin`. To reset it, see [[Security]].

**The page does not update live behind a proxy.**
The proxy buffers `/api/events`. For nginx/NPM the app sends `X-Accel-Buffering: no` itself;
for other proxies disable buffering for this path. Without the stream the page still updates by polling every 5 seconds.

**A site has no icon.**
The site is not reachable from the server either by its public address or through the backend, or it has no icon
(API services, for example). A failed lookup is retried after an hour. To clear the cache, delete `config/icons` and
restart the container. For a custom site you can set the icon URL manually.
