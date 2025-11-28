# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python client library for [CoplayDev/unity-mcp](https://github.com/CoplayDev/unity-mcp) - controls Unity Editor via TCP protocol. Single-file implementation with zero external dependencies (Python stdlib only).

## Commands

```bash
# Install globally
uv tool install .

# Run CLI
unity-mcp state --port 6401
unity-mcp console --types error --count 10
unity-mcp play --port 6401

# Run directly without install
python3 unity_mcp_client.py state --port 6401

# Test with uvx (after pushing to GitHub)
uvx --from git+https://github.com/bigdra50/unity-mcp-client unity-mcp state
```

## Architecture

### TCP Protocol

Unity MCP uses custom framing: **8-byte big-endian length header + JSON payload**

```
[8-byte length][{"type": "command_name", "params": {...}}]
```

Handshake: Server sends `WELCOME UNITY-MCP 1 FRAMING=1\n` on connect.

### API Patterns

**Tools** (write operations) - modify Unity state:
- `send_command("manage_editor", {"action": "play"})`
- `send_command("manage_gameobject", {"action": "create", ...})`

**Resources** (read-only) - query Unity state:
- `read_resource("get_editor_state")` → isPlaying, isCompiling, etc.
- `read_resource("get_tags")` → tag list
- `read_resource("get_layers")` → layer dict

Both use the same protocol; Resources just have different command names (e.g., `get_editor_state` vs `manage_editor`).

### Code Structure

```
unity_mcp_client.py
├── UnityMCPConnection    # TCP framing, send_command(), read_resource()
├── ConsoleAPI            # read_console operations
├── EditorAPI             # play/pause/stop + get_state/get_tags (Resources)
├── GameObjectAPI         # CRUD, find, components
├── SceneAPI              # load/save/hierarchy
├── AssetAPI              # create/modify/delete/search
├── UnityMCPClient        # Main client, aggregates all APIs
└── main()                # CLI entry point
```

## Key Implementation Details

- Port default: 6400 (configurable via `--port`)
- Timeout default: 5 seconds (configurable in UnityMCPClient constructor)
- Each command creates a new TCP connection (no persistent connections)
- Response format: `{"success": true, "message": "...", "data": {...}}`
