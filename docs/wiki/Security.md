# Security

## What is available without a password

Without logging in you can **view** the page: cards, search, source status. Everything that changes data requires the
admin password: settings, sources, custom sites, favorites, changing the password.

> If no password is set either in OpenBao or in `ADMIN_PASSWORD`, anyone who opens the page can change everything.
> The **Security** card shows a warning in that case.

## Admin password

- Stored in OpenBao (`secret/npm-dashboard/admin`) or in the `ADMIN_PASSWORD` variable — the variable takes precedence.
- Changed in **Settings → Security**: current password, new password (at least 8 characters) and confirmation.
  There is a generator and a strength meter. The new password takes effect immediately; the old one stops working.
- If the password comes from `ADMIN_PASSWORD`, it can only be changed in `.env`.
- A wrong password is answered with a 1-second delay to slow down brute force.
- The browser keeps the password until the tab is closed (`sessionStorage`). **Log out** removes it immediately.
- Any characters are allowed, including non-Latin ones (the header value is URL-encoded).

Reset a forgotten password:

```bash
docker exec -it -e BAO_ADDR=http://127.0.0.1:8200 openbao sh -c 'bao login && bao kv put secret/npm-dashboard/admin password=NEW_PASSWORD'
```

Home re-reads the password from OpenBao at least once a minute.

## NPM data

- The local database is opened read-only; the `meta` field (DNS provider keys) is never read or returned by the API.
- Use a dedicated account with minimal permissions for remote NPM instances.

## Icons

- The server looks up icons only for sites in the list — arbitrary URLs cannot be requested through `/api/icon`.
- Responses are checked by file signature; only images are served.
- SVG is served with `Content-Security-Policy: sandbox`, so scripts inside it do not run.

## Recommendations

- Do not expose Home to the internet without extra protection: add an NPM Access List or authentication.
- Publish it over HTTPS so the admin password is not sent in clear text.
- Keep the OpenBao port closed (`127.0.0.1`), as in the provided compose file.
