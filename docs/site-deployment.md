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
- mobile navigation, Autofix tabs, gallery dialog, and internal anchors work
- GitHub CTAs point to the public TraceGate repository
- console has no errors and no content exposes secrets or local paths

Public acceptance screenshots belong in `docs/site-screenshots/` and must be
regenerated after material visual changes.
