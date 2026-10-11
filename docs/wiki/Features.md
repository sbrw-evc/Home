# Features

## Cards and menu

- **Favorites** — sites marked with a star, always listed first.
- **All sites**, **Custom sites**, sections per **source** (when there are several) and per **domain**.
- Counters at the top: total, enabled, with HTTPS, shown. The **Grid** and **List** views are remembered in the browser.
- Cards changed in NPM are highlighted, and a notification shows how many were added, changed or removed.
- The menu collapses to icons (the `«` button at the bottom); on a phone it slides in from the left.
- The dot at the bottom of the menu: green — the event stream is connected, yellow — reconnecting, red — a source error.

## Search

The search bar is focused when the page opens.

| Action | Result |
|---|---|
| Typing | Filters cards by name, domains, forward address, description and group |
| `Enter` | Searches with the selected search engine; if an address is typed (`example.com`, `http://…`), opens it |
| `Ctrl`+`Enter` | Opens the first matching card |
| `Esc` | Clears the bar |
| `/` | Focuses the search bar from anywhere on the page |

The search engine is selected to the left of the bar and remembered in the browser. The default comes from the settings.
Custom search engines are added in **Settings → General**.

## Custom sites

The **+ Custom site** button: name, address (`http://` or `https://`), group (an NPM domain can be picked), description
and icon (optional). Edit or delete with the ✎ button on the card.

## Site icons

The server looks for an icon in this order:

1. the icon URL set for a custom site;
2. `<link rel="icon">` and `apple-touch-icon` on the site's main page (SVG first, then raster icons — larger is better, up to 256 px);
3. icons from the web manifest;
4. `/favicon.ico`.

The server first tries the site's public address. If it is not reachable from the server (for example, a router without
hairpin NAT), the request goes straight to the NPM host's backend with the right `Host` header; backend redirects to its
own domain are rewritten. Found icons are cached for 24 hours, misses for an hour. If the server finds nothing, the browser
tries `/favicon.ico` itself as a last resort; if that fails too, a letter on a colored background is shown.
