#!/usr/bin/env python3
"""headersHelper for the pollinations MCP server: print {"Authorization": "Bearer <key>"} as JSON on stdout.

The key is resolved exactly like `um polli` does: env POLLINATIONS_API_KEY, else the 'pollinations' entry in
the opencode auth.json. Claude Code runs this at connect time (see .mcp.json), so the key never has to be
exported into the environment. Exits 1 with a message on stderr when no key is found.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from um.polli import polli_key  # noqa: E402

print(json.dumps({"Authorization": f"Bearer {polli_key()}"}))
