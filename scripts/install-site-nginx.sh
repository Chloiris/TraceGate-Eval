#!/usr/bin/env bash

set -Eeuo pipefail

readonly DOMAIN="tracegate.chlogonia.xyz"
readonly SITE_ROOT="/var/www/tracegate"
readonly SOURCE_CONFIG="/tmp/tracegate.chlogonia.xyz.conf"
readonly STAGED_CONFIG="/root/tracegate.chlogonia.xyz.conf.staged"
readonly EXPECTED_CONFIG_SHA256="35712576a778d432070b5a9bc26e8767f4e0b545458019cd92040a5aed761d9e"
readonly AVAILABLE_CONFIG="/etc/nginx/sites-available/tracegate.chlogonia.xyz.conf"
readonly ENABLED_CONFIG="/etc/nginx/sites-enabled/tracegate.chlogonia.xyz.conf"

if [[ ${EUID} -ne 0 ]]; then
  echo "error: run this installer as root" >&2
  exit 1
fi

for command in nginx systemctl curl install ln cmp cp date apt-get sha256sum sed certbot; do
  if ! command -v "${command}" >/dev/null 2>&1 && [[ ${command} != certbot ]]; then
    echo "error: required command is missing: ${command}" >&2
    exit 1
  fi
done

if [[ ! -s "${SITE_ROOT}/index.html" ]]; then
  echo "error: ${SITE_ROOT}/index.html is missing or empty" >&2
  exit 1
fi

if [[ ! -s "${SOURCE_CONFIG}" ]]; then
  echo "error: reviewed Nginx config is missing at ${SOURCE_CONFIG}" >&2
  exit 1
fi

install -m 0600 "${SOURCE_CONFIG}" "${STAGED_CONFIG}"
trap 'rm -f "${STAGED_CONFIG}"' EXIT

actual_config_sha256="$(sha256sum "${STAGED_CONFIG}" | sed 's/[[:space:]].*$//')"
if [[ ${actual_config_sha256} != "${EXPECTED_CONFIG_SHA256}" ]]; then
  echo "error: Nginx config integrity check failed" >&2
  exit 1
fi

if [[ -e "${AVAILABLE_CONFIG}" ]] && ! cmp -s "${STAGED_CONFIG}" "${AVAILABLE_CONFIG}"; then
  backup="${AVAILABLE_CONFIG}.bak.$(date +%Y%m%d%H%M%S)"
  cp -a "${AVAILABLE_CONFIG}" "${backup}"
  echo "backed_up=${backup}"
fi

install -m 0644 "${STAGED_CONFIG}" "${AVAILABLE_CONFIG}"
ln -sfn "${AVAILABLE_CONFIG}" "${ENABLED_CONFIG}"

nginx -t
systemctl reload nginx

echo "http_local_check"
curl --fail --silent --show-error --head \
  -H "Host: ${DOMAIN}" http://127.0.0.1/ | sed -n '1,12p'

if ! command -v certbot >/dev/null 2>&1; then
  apt-get install -y certbot python3-certbot-nginx
fi

certbot --nginx \
  --domain "${DOMAIN}" \
  --non-interactive \
  --agree-tos \
  --redirect \
  --register-unsafely-without-email

nginx -t
systemctl reload nginx

echo "https_public_check"
curl --fail --silent --show-error --head "https://${DOMAIN}/" | sed -n '1,16p'
echo "deployment_complete=https://${DOMAIN}"
