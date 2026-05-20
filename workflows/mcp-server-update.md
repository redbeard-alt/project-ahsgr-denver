# Workflow: MCP Server Update

Regenerate or update the FastMCP server after schema changes or new tools.

## Trigger

- New index CSV added (e.g. `docs/officer_history.csv`)
- Column names changed in `docs/roster_index.csv`
- Adding a new search tool to the server

## Steps

1. Run the `mcp-builder` agent (`.claude/agents/mcp-builder.md`)
2. Validate: `make test`
3. Restart server in openclaw:

```bash
openclaw gateway restart ashgr-denver-corpus
# or full re-register:
openclaw gateway register \
  --name ashgr-denver-corpus \
  --command ".venv/bin/python lib/ashgr_mcp_server.py" \
  --cwd ~/Laboratory/project-ashgr-denver
```

4. Test via openclaw-agent: `make configure --client ahsgr-north-denver`
