# Optional Webhook Relay

The relay is an optional, separate FastAPI service for installations that need
GitHub webhook delivery. TraceGate Studio continues bounded local polling when
the relay is absent and displays `Webhook Relay 未配置`.

## Security model

- GitHub requests are accepted only with a valid `X-Hub-Signature-256` over
  the exact body and a bounded `X-GitHub-Delivery` identifier.
- Delivery identifiers are deduplicated; replaying an identifier with different
  content is rejected.
- An administrator creates a ten-minute, one-use pairing code scoped to an
  explicit list of `owner/repository` names.
- Pairing returns a random device bearer token once. Only its SHA-256 digest is
  retained in relay memory.
- The SSE endpoint requires that device token and emits only bounded event
  metadata for repositories assigned during pairing.
- In-memory pairing/device/dedup state intentionally resets on restart. A
  production multi-instance deployment must replace it with a shared durable
  store before claiming high availability.
- TLS is mandatory outside loopback. Put the relay behind an HTTPS reverse
  proxy; never expose the compose file's plain HTTP port to the public network.

## Local configuration

Generate two independent secrets with at least 32 characters, configure the
GitHub webhook content type as `application/json`, and start the loopback-only
container:

```bash
export TRACEGATE_RELAY_ADMIN_TOKEN="$(openssl rand -hex 32)"
export TRACEGATE_RELAY_GITHUB_SECRET="$(openssl rand -hex 32)"
docker compose -f docker-compose.webhook-relay.yml up --build
curl http://127.0.0.1:8080/health
```

Create a one-use pairing code:

```bash
curl -X POST http://127.0.0.1:8080/v1/pairing-codes \
  -H "Authorization: Bearer $TRACEGATE_RELAY_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"repositories":["owner/repository"]}'
```

Exchange the returned code at `POST /v1/devices/pair`, store the returned
device token in the operating-system credential store, then connect to
`GET /v1/events` with `Authorization: Bearer <device-token>`.

The service's local integration tests run with `pytest
tests/test_webhook_relay.py`. Docker execution remains unverified on hosts
without Docker.
