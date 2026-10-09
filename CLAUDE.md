@AGENTS.md

## Claude Code specifics
- Installed as a plugin, the skills are namespaced (`/universal-modder:mod-any-game`), the pollinations MCP server
  comes from `.mcp.json`, whose `headersHelper` (`bin/polli-mcp-headers.py`) finds the key like `um polli`:
  `POLLINATIONS_API_KEY`, else the opencode `auth.json`, and a SessionStart hook puts `um` on PATH.
- In a clone, `.claude/settings.json` adds the same PATH hook and `.claude/skills` links to `skills/`.
