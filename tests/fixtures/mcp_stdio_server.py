from __future__ import annotations

import json
import sys


for line in sys.stdin:
    message = json.loads(line)
    method = message.get("method")
    if method == "notifications/initialized":
        continue
    request_id = message["id"]
    if method == "initialize":
        result = {
            "protocolVersion": "2025-11-25",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "tracegate-test", "version": "1.0.0"},
        }
    elif method == "tools/list":
        result = {
            "tools": [
                {"name": "echo", "description": "Echo arguments", "inputSchema": {"type": "object"}},
                {"name": "hidden", "description": "Not allowlisted", "inputSchema": {"type": "object"}},
            ]
        }
    elif method == "tools/call":
        result = {
            "content": [{"type": "text", "text": json.dumps(message["params"]["arguments"], sort_keys=True)}],
            "structuredContent": message["params"]["arguments"],
            "isError": False,
        }
    else:
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32601, "message": "Method not found"},
        }
        sys.stdout.write(json.dumps(response, separators=(",", ":")) + "\n")
        sys.stdout.flush()
        continue
    response = {"jsonrpc": "2.0", "id": request_id, "result": result}
    sys.stdout.write(json.dumps(response, separators=(",", ":")) + "\n")
    sys.stdout.flush()
