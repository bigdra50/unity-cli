# Domain Reload Resilience Design

ドメインリロード問題の根本解決のための詳細設計ドキュメント。

## 1. 問題分析

### 1.1 現状の問題点

#### 問題1: Fire-and-forget STATUS送信

```
beforeAssemblyReload → Task.Run(SendReloadingStatus) → ドメインリロード開始
                              ↓
                      (STATUS送信が完了する前にプロセス中断)
```

`BridgeReloadHandler.cs` L81-91:
```csharp
_ = Task.Run(async () =>
{
    try
    {
        await manager.Client.SendReloadingStatusAsync().ConfigureAwait(false);
    }
    catch
    {
        // Ignore - connection may be lost during reload anyway
    }
});
```

この実装では、`Task.Run`による非同期送信がドメインリロード開始前に完了する保証がない。

#### 問題2: Grace periodがSTATUS受信に依存

`instance_registry.py` L278-279:
```python
was_reloading = instance.status == InstanceStatus.RELOADING
if was_reloading and grace_period_ms > 0:
```

STATUS "reloading"が到達しなければ、grace periodは適用されず、インスタンスは即座に切断される。

#### 問題3: タイムアウトの矛盾

| Component | Timeout |
|-----------|---------|
| CLI socket | 5秒 (デフォルト) |
| Server reload timeout | 30秒 |
| Server grace period | 60秒 |
| CLI retry max time | 30秒 |

CLIのソケットタイムアウト(5秒)がサーバーの待機時間より短いため、サーバー側で待機していてもCLIがタイムアウトする。

### 1.2 unity-mcpの解決策分析

unity-mcpでは以下の3つのアプローチで解決:

1. **ファイルベースのステータス通知**
   - `~/.unity-mcp/unity-mcp-status-{hash}.json`にステータスを書き込み
   - TCP送信が失敗しても、ファイルは確実に書き込まれる
   - サーバーはファイルを監視してステータスを取得

2. **同期的なステータス書き込み**
   ```csharp
   // StdioBridgeReloadHandler.cs
   try { stopTask.Wait(500); } catch { }  // 同期待機
   StdioBridgeHost.WriteHeartbeat(true, "reloading");  // ファイル書き込み
   ```

3. **サーバー側のポーリング待機**
   ```python
   # unity_connection.py
   status = read_status_file(target_hash)
   if status and status.get('reloading'):
       return MCPResponse(success=False, error="Unity is reloading; please retry", hint="retry")
   ```

## 2. 設計方針

### 2.1 選択: ハイブリッドアプローチ

TCP単体でもファイル単体でもなく、両方を組み合わせる:

| 方式 | 長所 | 短所 |
|------|------|------|
| TCPのみ | シンプル、リアルタイム | 送信失敗リスク |
| ファイルのみ | 確実 | ポーリング遅延 |
| ハイブリッド | 確実性と即時性の両立 | 実装複雑度 |

### 2.2 設計原則

1. **STATUS送信は同期的に完了を待つ** - ドメインリロード開始前に確実に送信
2. **ファイルをフォールバックとして使用** - TCP送信が失敗してもファイルで通知
3. **サーバー側で自動grace period** - 接続切断時にインスタンスの前状態を考慮
4. **タイムアウトの一貫性** - CLI/Server間のタイムアウト整合

## 3. アーキテクチャ設計

### 3.1 状態遷移図 (改善版)

```
                                 DISCONNECTED
                                      │
                                      │ REGISTER
                                      ▼
    ┌───────────────────────────── READY ◄──────────────────────────┐
    │                                 │                              │
    │ STATUS "reloading"              │ COMMAND                      │
    │ or file write                   ▼                              │
    │                               BUSY ────── COMMAND_RESULT ──────┤
    ▼                                                                │
RELOADING ─────────────────── (reconnect within grace) ──────────────┘
    │
    │ (grace period expired without reconnect)
    ▼
DISCONNECTED
```

### 3.2 新しいシーケンス図

```
Unity                    Relay Server                CLI
  │                           │                        │
  │ [Domain Reload開始検知]     │                        │
  │                           │                        │
  │──sync STATUS "reloading"─→│                        │
  │  (タイムアウト: 500ms)      │                        │
  │                           │                        │
  │──write status.json───────→│                        │
  │  (同期書き込み)             │                        │
  │                           │                        │
  │ [TCP接続切断]               │                        │
  │        X                  │                        │
  │                           │                        │
  │                           │◄──────REQUEST─────────│
  │                           │                        │
  │                           │──(check file for      │
  │                           │   reloading status)   │
  │                           │                        │
  │                           │ [wait for reconnect    │
  │                           │  or grace period]      │
  │                           │                        │
  │ [Domain Reload完了]        │                        │
  │                           │                        │
  │──REGISTER────────────────→│                        │
  │                           │                        │
  │◄──REGISTERED──────────────│                        │
  │                           │                        │
  │──STATUS "ready"──────────→│                        │
  │  (or delete status.json)  │                        │
  │                           │                        │
  │◄─────────COMMAND──────────│                        │
  │                           │                        │
  │──COMMAND_RESULT──────────→│                        │
  │                           │                        │
  │                           │─────RESPONSE──────────→│
  │                           │                        │
```

### 3.3 ステータスファイル仕様

**パス**: `~/.unity-bridge/status-{instance_hash}.json`

**フォーマット**:
```json
{
  "instance_id": "/Users/dev/MyProject",
  "project_name": "MyProject",
  "unity_version": "2022.3.0f1",
  "status": "reloading",
  "relay_host": "127.0.0.1",
  "relay_port": 6500,
  "timestamp": "2024-01-26T12:00:00.000Z",
  "seq": 42
}
```

| Field | Type | Description |
|-------|------|-------------|
| instance_id | string | プロジェクトパス |
| project_name | string | プロジェクト名 |
| unity_version | string | Unityバージョン |
| status | string | "ready" / "reloading" |
| relay_host | string | Relay Serverホスト |
| relay_port | int | Relay Serverポート |
| timestamp | string | ISO 8601形式のタイムスタンプ |
| seq | int | シーケンス番号 (変更検知用) |

## 4. プロトコル変更

### 4.1 既存プロトコルとの互換性

プロトコル自体は変更しない。以下は実装の変更のみ:

1. STATUS "reloading"は同期的に送信を試みる
2. ファイルベースのフォールバックを追加
3. サーバー側でファイル監視を追加

### 4.2 新しいタイムアウト設定

**推奨値**:

| Parameter | Current | Proposed |
|-----------|---------|----------|
| CLI socket timeout | 5s | 15s |
| CLI retry_max_time_ms | 30s | 45s |
| Server wait_for_ready_ms | 10s | 15s |
| Server grace_period_ms | 60s | 60s (変更なし) |
| Unity STATUS send timeout | - | 500ms |

## 5. 実装詳細

### 5.1 Unity側 (C#) 変更

#### 5.1.1 新規ファイル: `BridgeStatusFile.cs`

```csharp
using System;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using Newtonsoft.Json;
using UnityEngine;

namespace UnityBridge.Helpers
{
    /// <summary>
    /// Manages status file for reliable domain reload notification.
    /// Status file is used as fallback when TCP notification fails.
    /// </summary>
    public static class BridgeStatusFile
    {
        private const string StatusDirName = ".unity-bridge";
        private static int _seq = 0;

        private static string GetStatusDir()
        {
            var envDir = Environment.GetEnvironmentVariable("UNITY_BRIDGE_STATUS_DIR");
            if (!string.IsNullOrWhiteSpace(envDir))
                return envDir;

            var home = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
            return Path.Combine(home, StatusDirName);
        }

        private static string ComputeInstanceHash(string instanceId)
        {
            using var sha1 = SHA1.Create();
            var bytes = Encoding.UTF8.GetBytes(instanceId ?? string.Empty);
            var hashBytes = sha1.ComputeHash(bytes);
            var sb = new StringBuilder();
            for (int i = 0; i < 4; i++)
            {
                sb.Append(hashBytes[i].ToString("x2"));
            }
            return sb.ToString();
        }

        public static string GetStatusFilePath(string instanceId)
        {
            var dir = GetStatusDir();
            var hash = ComputeInstanceHash(instanceId);
            return Path.Combine(dir, $"status-{hash}.json");
        }

        /// <summary>
        /// Write status file synchronously.
        /// Called before domain reload to ensure status is persisted.
        /// </summary>
        public static void WriteStatus(
            string instanceId,
            string projectName,
            string unityVersion,
            string status,
            string relayHost,
            int relayPort)
        {
            try
            {
                var dir = GetStatusDir();
                Directory.CreateDirectory(dir);

                var filePath = GetStatusFilePath(instanceId);
                var payload = new
                {
                    instance_id = instanceId,
                    project_name = projectName,
                    unity_version = unityVersion,
                    status = status,
                    relay_host = relayHost,
                    relay_port = relayPort,
                    timestamp = DateTime.UtcNow.ToString("O"),
                    seq = ++_seq
                };

                var json = JsonConvert.SerializeObject(payload);
                File.WriteAllText(filePath, json, new UTF8Encoding(false));

                BridgeLog.Verbose($"Status file written: {status}");
            }
            catch (Exception ex)
            {
                BridgeLog.Warn($"Failed to write status file: {ex.Message}");
            }
        }

        /// <summary>
        /// Delete status file.
        /// Called when Unity quits or connection is intentionally closed.
        /// </summary>
        public static void DeleteStatus(string instanceId)
        {
            try
            {
                var filePath = GetStatusFilePath(instanceId);
                if (File.Exists(filePath))
                {
                    File.Delete(filePath);
                    BridgeLog.Verbose("Status file deleted");
                }
            }
            catch (Exception ex)
            {
                BridgeLog.Warn($"Failed to delete status file: {ex.Message}");
            }
        }
    }
}
```

#### 5.1.2 修正: `BridgeReloadHandler.cs`

```csharp
using System;
using System.Threading;
using System.Threading.Tasks;
using UnityBridge.Helpers;
using UnityEditor;

namespace UnityBridge
{
    [InitializeOnLoad]
    public static class BridgeReloadHandler
    {
        private const string SessionStateKeyWasConnected = "UnityBridge.ReloadHandler.WasConnected";
        private const string SessionStateKeyLastHost = "UnityBridge.ReloadHandler.LastHost";
        private const string SessionStateKeyLastPort = "UnityBridge.ReloadHandler.LastPort";

        // STATUS送信のタイムアウト (ドメインリロード前に完了する必要があるため短め)
        private const int StatusSendTimeoutMs = 500;

        private static bool WasConnected
        {
            get => SessionState.GetBool(SessionStateKeyWasConnected, false);
            set => SessionState.SetBool(SessionStateKeyWasConnected, value);
        }

        private static string LastHost
        {
            get => SessionState.GetString(SessionStateKeyLastHost, "127.0.0.1");
            set => SessionState.SetString(SessionStateKeyLastHost, value);
        }

        private static int LastPort
        {
            get => SessionState.GetInt(SessionStateKeyLastPort, ProtocolConstants.DefaultPort);
            set => SessionState.SetInt(SessionStateKeyLastPort, value);
        }

        static BridgeReloadHandler()
        {
            AssemblyReloadEvents.beforeAssemblyReload += OnBeforeAssemblyReload;
            AssemblyReloadEvents.afterAssemblyReload += OnAfterAssemblyReload;
            EditorApplication.quitting += OnEditorQuitting;

            BridgeLog.Verbose("Reload handler initialized");
        }

        public static void RegisterClient(RelayClient client, string host, int port)
        {
            if (client != null && client.IsConnected)
            {
                WasConnected = true;
                LastHost = host;
                LastPort = port;
            }
        }

        public static void UnregisterClient()
        {
            WasConnected = false;
        }

        private static void OnBeforeAssemblyReload()
        {
            BridgeLog.Verbose("Before assembly reload");

            var manager = BridgeManager.Instance;
            if (manager != null && manager.Client != null && manager.Client.IsConnected)
            {
                WasConnected = true;
                LastHost = manager.Host;
                LastPort = manager.Port;

                // 1. 同期的にSTATUS "reloading"を送信 (タイムアウト付き)
                try
                {
                    using var cts = new CancellationTokenSource(StatusSendTimeoutMs);
                    var task = manager.Client.SendReloadingStatusAsync();
                    task.Wait(cts.Token);
                    BridgeLog.Verbose("STATUS reloading sent successfully");
                }
                catch (OperationCanceledException)
                {
                    BridgeLog.Warn("STATUS send timed out, relying on status file");
                }
                catch (Exception ex)
                {
                    BridgeLog.Warn($"STATUS send failed: {ex.Message}, relying on status file");
                }

                // 2. ステータスファイルを書き込み (フォールバック)
                BridgeStatusFile.WriteStatus(
                    manager.Client.InstanceId,
                    manager.Client.ProjectName,
                    manager.Client.UnityVersion,
                    "reloading",
                    LastHost,
                    LastPort);
            }
        }

        private static void OnAfterAssemblyReload()
        {
            BridgeLog.Verbose("After assembly reload");

            if (WasConnected)
            {
                WasConnected = false;
                var host = LastHost;
                var port = LastPort;

                void ReconnectOnUpdate()
                {
                    EditorApplication.update -= ReconnectOnUpdate;
                    ReconnectAsync(host, port);
                }

                EditorApplication.update += ReconnectOnUpdate;
            }
        }

        private static async void ReconnectAsync(string host, int port)
        {
            if (string.IsNullOrEmpty(host) || port <= 0)
            {
                BridgeLog.Error($"Reconnection failed: invalid parameters (host={host}, port={port})");
                return;
            }

            try
            {
                var manager = BridgeManager.Instance;
                if (manager == null)
                {
                    BridgeLog.Error("Reconnection failed: BridgeManager.Instance is null");
                    return;
                }

                await manager.ConnectAsync(host, port);
                BridgeLog.Verbose("Reconnected after reload");

                if (manager.Client != null && manager.Client.IsConnected)
                {
                    // STATUS "ready"を送信
                    await manager.Client.SendReadyStatusAsync();

                    // ステータスファイルを "ready" に更新
                    BridgeStatusFile.WriteStatus(
                        manager.Client.InstanceId,
                        manager.Client.ProjectName,
                        manager.Client.UnityVersion,
                        "ready",
                        host,
                        port);
                }
            }
            catch (Exception ex)
            {
                BridgeLog.Error($"Reconnection failed: {ex.Message}");
            }
        }

        private static void OnEditorQuitting()
        {
            BridgeLog.Verbose("Editor quitting");

            var manager = BridgeManager.Instance;
            if (manager != null)
            {
                // ステータスファイルを削除
                if (manager.Client != null)
                {
                    BridgeStatusFile.DeleteStatus(manager.Client.InstanceId);
                }

                // 同期的に切断を試みる (短いタイムアウト)
                try
                {
                    using var cts = new CancellationTokenSource(500);
                    var task = manager.DisconnectAsync();
                    task.Wait(cts.Token);
                }
                catch
                {
                    // Ignore - editor is quitting anyway
                }
            }

            WasConnected = false;
        }
    }
}
```

### 5.2 Relay Server側 (Python) 変更

#### 5.2.1 新規ファイル: `relay/status_file.py`

```python
"""
Status File Reader

Reads Unity instance status from file-based notifications.
Used as fallback when TCP status notification fails.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StatusFileContent:
    """Parsed content of a status file"""

    instance_id: str
    project_name: str
    unity_version: str
    status: str  # "ready" or "reloading"
    relay_host: str
    relay_port: int
    timestamp: datetime
    seq: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StatusFileContent:
        timestamp_str = data.get("timestamp", "")
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            timestamp = datetime.utcnow()

        return cls(
            instance_id=data.get("instance_id", ""),
            project_name=data.get("project_name", ""),
            unity_version=data.get("unity_version", ""),
            status=data.get("status", "ready"),
            relay_host=data.get("relay_host", "127.0.0.1"),
            relay_port=data.get("relay_port", 6500),
            timestamp=timestamp,
            seq=data.get("seq", 0),
        )


def get_status_dir() -> Path:
    """Get status file directory"""
    env_dir = os.environ.get("UNITY_BRIDGE_STATUS_DIR")
    if env_dir:
        return Path(env_dir)
    return Path.home() / ".unity-bridge"


def compute_instance_hash(instance_id: str) -> str:
    """Compute 8-char hash from instance ID"""
    hash_bytes = hashlib.sha1(instance_id.encode("utf-8")).digest()
    return hash_bytes[:4].hex()


def get_status_file_path(instance_id: str) -> Path:
    """Get path to status file for an instance"""
    hash_str = compute_instance_hash(instance_id)
    return get_status_dir() / f"status-{hash_str}.json"


def read_status_file(instance_id: str) -> StatusFileContent | None:
    """
    Read status file for a specific instance.

    Returns None if file doesn't exist or is invalid.
    """
    try:
        file_path = get_status_file_path(instance_id)
        if not file_path.exists():
            return None

        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        return StatusFileContent.from_dict(data)
    except (json.JSONDecodeError, OSError) as e:
        logger.debug(f"Failed to read status file for {instance_id}: {e}")
        return None


def read_all_status_files() -> list[StatusFileContent]:
    """
    Read all status files in the status directory.

    Returns list of status file contents, sorted by timestamp (newest first).
    """
    status_dir = get_status_dir()
    if not status_dir.exists():
        return []

    results: list[StatusFileContent] = []
    for file_path in status_dir.glob("status-*.json"):
        try:
            with file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            results.append(StatusFileContent.from_dict(data))
        except (json.JSONDecodeError, OSError) as e:
            logger.debug(f"Failed to read status file {file_path}: {e}")

    # Sort by timestamp, newest first
    results.sort(key=lambda x: x.timestamp, reverse=True)
    return results


def is_instance_reloading(instance_id: str, max_age_seconds: float = 120.0) -> bool:
    """
    Check if an instance is currently reloading.

    Args:
        instance_id: Instance ID to check
        max_age_seconds: Maximum age of status file to consider valid

    Returns:
        True if status file indicates reloading and is recent enough
    """
    status = read_status_file(instance_id)
    if status is None:
        return False

    if status.status != "reloading":
        return False

    # Check if status is too old (likely stale)
    age = (datetime.utcnow() - status.timestamp.replace(tzinfo=None)).total_seconds()
    if age > max_age_seconds:
        logger.debug(f"Status file for {instance_id} is stale ({age:.1f}s old)")
        return False

    return True
```

#### 5.2.2 修正: `relay/instance_registry.py` (差分)

```python
# 先頭に追加
from .status_file import is_instance_reloading

# disconnect_with_grace_period メソッドを修正
async def disconnect_with_grace_period(
    self,
    instance_id: str,
    grace_period_ms: int,
) -> None:
    instance = self._instances.get(instance_id)
    if not instance:
        return

    # TCPステータスとファイルステータスの両方をチェック
    was_reloading = instance.status == InstanceStatus.RELOADING

    # ファイルベースのステータスもチェック (TCP送信が失敗していた場合のフォールバック)
    if not was_reloading:
        was_reloading = is_instance_reloading(instance_id)
        if was_reloading:
            logger.info(f"Instance {instance_id} detected as reloading via status file")

    was_default = self._default_instance_id == instance_id
    # ... 以降は既存の処理
```

#### 5.2.3 修正: `relay/server.py` (差分)

```python
# _execute_command メソッド内、ループの先頭に追加
from .status_file import is_instance_reloading

# max_wait_ms を 10000 から 15000 に変更
max_wait_ms = 15000

# インスタンスが見つからない場合のチェックを追加
if not instance:
    # インスタンスが見つからない場合、ステータスファイルをチェック
    if instance_id and is_instance_reloading(instance_id):
        if waited_ms == 0:
            logger.info(f"[{request_id}] Instance {instance_id} is reloading (via status file), waiting...")
        await asyncio.sleep(poll_interval_ms / 1000)
        waited_ms += poll_interval_ms
        continue
```

### 5.3 CLI側 (Python) 変更

#### 5.3.1 修正: `unity_cli/config.py`

```python
# タイムアウト設定の変更
DEFAULT_SOCKET_TIMEOUT = 15.0  # 5.0 → 15.0
DEFAULT_RETRY_MAX_TIME_MS = 45000  # 30000 → 45000
```

## 6. テスト計画

### 6.1 ドメインリロードテストシナリオ

| # | シナリオ | 期待結果 |
|---|----------|----------|
| 1 | 通常のドメインリロード (STATUS成功) | grace period適用、再接続成功 |
| 2 | STATUS送信タイムアウト | ファイルフォールバック、grace period適用 |
| 3 | ファイル書き込みも失敗 | grace periodなし、即切断 |
| 4 | リロード中にコマンド送信 | サーバーが待機、再接続後に実行 |
| 5 | grace period超過 | エラー返却 |
| 6 | エディタ終了 | ファイル削除、即切断 |

### 6.2 エッジケーステスト

| ケース | 期待動作 |
|--------|----------|
| 古いステータスファイル (120秒以上) | 無視 |
| 複数インスタンスの同時リロード | 各インスタンス独立管理 |
| ステータスディレクトリ不存在 | 自動作成 |
| 権限エラー | ログ出力、TCP依存 |

## 7. 移行計画

### Phase 1: 後方互換実装 (Week 1-2)

- ステータスファイル機能を追加 (フォールバックとして)
- 既存TCPベースの動作は維持
- サーバーでファイル読み取りを補助的に追加

### Phase 2: タイムアウト調整 (Week 3)

- CLIタイムアウトを延長
- サーバー待機時間を調整
- 設定ファイルでカスタマイズ可能に

### Phase 3: 同期STATUS送信 (Week 4)

- Unity側で同期送信に変更
- テスト期間後、デフォルト動作に

## 8. 設定

### 8.1 環境変数

| Variable | Default | Description |
|----------|---------|-------------|
| UNITY_BRIDGE_STATUS_DIR | ~/.unity-bridge | ステータスファイルディレクトリ |
| UNITY_BRIDGE_GRACE_PERIOD_MS | 60000 | Grace period (ミリ秒) |

## 9. まとめ

### 主要な変更点

1. **Unity側**: 同期STATUS送信 + ファイルフォールバック
2. **Server側**: ファイル監視によるステータス補完
3. **CLI側**: タイムアウト延長

### 期待される改善

- ドメインリロード時のコマンド成功率向上
- 再接続の信頼性向上
- エラーメッセージの明確化
