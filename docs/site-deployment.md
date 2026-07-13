# TraceGate marketing site deployment

The site is a pure static Vite build. Deployment is intentionally limited to
`/var/www/tracegate`; it does not touch the personal site, blog, or any other
directory under `/var/www`.

## Routine deployment

```bash
pnpm install --frozen-lockfile
pnpm site:lint
pnpm site:typecheck
pnpm site:test
pnpm site:build
pnpm site:test:e2e
pnpm site:lighthouse
pnpm site:deploy
```

`scripts/deploy-site.sh` verifies the repository and build, checks the
`tracegate-server` SSH alias in batch mode, requires the remote directory to
exist and be writable, prints file count/size, and runs `rsync -az --delete`
against only `/var/www/tracegate/`. It then checks `index.html` and the public
HTTP/HTTPS status. SSH failure stops the deployment.

The script does not read private keys, request a root password, or edit Nginx.

## Initial Nginx setup (root terminal only)

The reviewed server block is
`infra/nginx/tracegate.chlogonia.xyz.conf`. If the server has no equivalent
configuration, an administrator can run:

```bash
sudo install -m 0644 infra/nginx/tracegate.chlogonia.xyz.conf \
  /etc/nginx/sites-available/tracegate.chlogonia.xyz.conf
sudo ln -s /etc/nginx/sites-available/tracegate.chlogonia.xyz.conf \
  /etc/nginx/sites-enabled/tracegate.chlogonia.xyz.conf
sudo nginx -t
sudo systemctl reload nginx
```

Run those commands on the server from a trusted copy of the repository, or
copy the reviewed config through the administrator's normal change process.
Do not grant the deployment account root access.

`scripts/install-site-nginx.sh` packages the same one-time administrator flow
for the dedicated TraceGate host. It refuses non-root execution, stages and
hash-verifies the reviewed config before installation, backs up a changed
TraceGate config, tests Nginx before reload, and only then attempts Certbot. It
does not alter any other virtual host. The routine deploy account remains
unprivileged and never executes this script automatically.

The config provides SPA fallback, hashed asset caching, bounded media caching,
gzip, no-cache HTML, and conservative security headers.

## HTTPS (root terminal only)

After DNS resolves and HTTP serves the correct site:

```bash
sudo certbot --nginx -d tracegate.chlogonia.xyz
sudo nginx -t
sudo systemctl reload nginx
curl -I https://tracegate.chlogonia.xyz
```

Certbot is an administrator action. A failed HTTPS check must remain reported
as unavailable; the deployment script never treats upload alone as TLS success.

## Acceptance

Confirm:

- HTTP and HTTPS return 200
- title is `TraceGate Studio — Evidence-grounded AI Coding Agent`
- JavaScript, CSS, AVIF/WebP, favicon, robots, sitemap, and OG image load
- Chinese is the default and English switches without reload
- a clean browser context paints light before React starts
- the header toggle switches both directions without reloading or moving scroll
- `tracegate-site-theme` persists light/dark across refresh and rejects invalid values
- mobile navigation and the gallery dialog stay open during a theme change
- mobile navigation, Autofix tabs, gallery dialog, and internal anchors work
- GitHub CTAs point to the public TraceGate repository
- console has no errors and no content exposes secrets or local paths

Public acceptance screenshots belong in `docs/site-screenshots/` and must be
regenerated after material visual changes.

The required paired captures are:

- `light-desktop-1440-home.png` / `dark-desktop-1440-home.png`
- `light-desktop-autofix.png` / `dark-desktop-autofix.png`
- `light-mobile-390-home.png` / `dark-mobile-390-home.png`
- `light-mobile-navigation.png` / `dark-mobile-navigation.png`

At the time the theme system was prepared, the origin Nginx served the site but
the public hostname was still intercepted by the cloud provider's ICP filing
gate. Upload success must not be reported as public acceptance until that
external gate is removed and HTTP/HTTPS checks both complete.
