# Minimal Output Example

This is the smallest acceptable response shape for `examples/minimal_input.json`.

```text
===PATCH===

===TRACEGATE_DECISION===
decision: verify_first
evidence_used:
- Client version telemetry is unavailable.
- No owner has confirmed whether legacyToken is still consumed.
risks:
- Removing legacyToken without evidence could break old login clients.
verification_plan:
- Check gateway telemetry for legacyToken readers.
- Add a characterization test for the login response JSON shape.
- Use owner review or a feature flag before deleting the compatibility path.
```
