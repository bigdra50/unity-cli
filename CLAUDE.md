# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Unity CLI + Relay Server for controlling Unity Editor via TCP. Supports multiple Unity instances with domain reload resilience.

```
CLI ←──TCP:6500──→ Relay Server (Python) ←──TCP:6500──→ Unity Editor(s)
```

## Commands

```bash
# Install globally (provides: unity-cli, u, unity commands)
uv tool install .

# Run Relay Server standalone
unity-relay --port 6500
```

All subcommands are self-documenting: `u --help`, `u <command> --help`.

Frequently used:

```bash
u state                                   # Get editor state
u play / u stop / u pause                 # Playmode control
u refresh                                 # Refresh AssetDatabase
u screenshot -s game -p ./out.png         # Capture screenshot
u screenshot --burst -n 10                # Burst capture
u console get -l E                        # Error logs
u scene hierarchy                         # Scene hierarchy
u tests run edit                          # Run EditMode tests
u recorder start --fps 30                 # Start frame recording
u recorder stop                           # Stop recording
u uitree dump -p "GameView"               # UI Toolkit tree
```

## Architecture

### State Machine

```
DISCONNECTED → (REGISTER) → READY → (COMMAND) → BUSY → (COMMAND_RESULT) → READY
                              ↓                                              ↑
                        (beforeReload)                              (afterReload)
                              ↓                                              ↑
                          RELOADING ─────────────────────────────────────────┘
```

## Key Implementation Details

### Relay Server

- Port: 6500 (default)
- Heartbeat: 5s interval, 15s timeout, 3 retries
- RELOADING timeout: 30s (extended)
- Single Outstanding PING rule
- Queue: FIFO, max 10, disabled by default
- Idempotency: cache success responses for 60s

### CLI

- Exponential backoff: 500ms → 1s → 2s → 4s → 8s (max 45s total)
- Retryable errors: INSTANCE_RELOADING, INSTANCE_BUSY, TIMEOUT
- request_id format: `{client_id}:{uuid}`

### Unity Bridge

- Instance ID: `Path.GetFullPath(Application.dataPath + "/..")`
- Domain reload: STATUS "reloading" → reconnect → REGISTER
- [BridgeTool("command_name")] attribute for auto-discovery

## Protocol Spec

See `docs/protocol-spec.md` for full specification.

## Testing

バグ修正・機能追加はテストファーストで進める。

1. 再現テストを書く (RED)
2. テスト実行で失敗を確認
3. 実装を修正 (GREEN)
4. テスト実行で成功を確認
5. コミット

### Python (Relay Server / CLI)

```bash
# 全テスト実行
uv run python -m pytest tests/

# 特定ファイル
uv run python -m pytest tests/test_scene_api.py

# 特定テスト
uv run python -m pytest tests/test_scene_api.py -k "test_hierarchy"
```

### Unity (C# / UnityBridge)

TestProject が Unity テスト用プロジェクト。Relay 経由で Unity Editor 上の Test Runner を実行する。

```bash
# コンパイル確認
u -i TestProject refresh
u -i TestProject console get -l E

# EditMode テスト
u -i TestProject tests run edit                           # 全件
u -i TestProject tests run edit -a "Game.Tests.Editor"    # アセンブリ指定
u -i TestProject tests run edit -g "SceneTest"            # クラス名パターン
u -i TestProject tests run edit -n "HandleCommand_Hierarchy_ItemsCountDoesNotExceedPageSize"  # テスト名指定

# PlayMode テスト
u -i TestProject tests run play

# テスト一覧
u -i TestProject tests list edit
```

テスト配置:

| テスト対象 | テストの場所 | asmdef |
|-----------|-------------|--------|
| `relay/`, `unity_cli/` | `tests/` | - (pytest) |
| `UnityBridge/Editor/` | `TestProject/Assets/Tests/Editor/` | `Game.Tests.Editor` |
| Runtime スクリプト | `TestProject/Assets/Tests/PlayMode/` | `Game.Tests.PlayMode` |
