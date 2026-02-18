# Unity Bridge Protocol Specification v1.0

## Overview

Unity EditorをCLIから操作するためのブリッジプロトコル仕様。

```
CLI ←──TCP:6500──→ Relay Server ←──TCP:6500──→ Unity Editor(s)
```

## Design Principles

- ゼロベース設計（既存実装との互換性は考慮しない）
- シンプルさ優先
- ドメインリロード耐性
- 複数Unityインスタンス対応

## Framing

全通信共通: **4-byte big-endian length prefix + JSON payload**

```
┌────────────────────────────────────┐
│ 4-byte Length (big-endian, uint32) │
├────────────────────────────────────┤
│ JSON Payload (UTF-8)               │
└────────────────────────────────────┘
```

- 最大ペイロードサイズ: 16 MiB
- エンコーディング: UTF-8
- バイトオーダー: Big-endian

### Error Handling

| 状況 | 挙動 |
|------|------|
| ペイロード > 16MiB | 接続切断 + ログ出力 |
| 不正なJSON | 接続切断 + ログ出力（idが取得できないため） |
| Length不一致 | 接続切断 + ログ出力 |
| idが取得できるパースエラー | ERRORメッセージ返却 (code: `MALFORMED_JSON`) |

Note: idフィールドが取得できない場合はERRORメッセージを返却できないため、接続切断のみ行う。

## Message Types

### Common Fields

全メッセージに含まれるフィールド:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | Yes | メッセージタイプ |
| `ts` | int64 | No | Unix timestamp (ms) |

---

## Unity → Relay Messages

### REGISTER

Unity起動時に中継サーバーへ登録。

```json
{
  "type": "REGISTER",
  "protocol_version": "1.0",
  "instance_id": "/Users/dev/MyGame",
  "project_name": "MyGame",
  "unity_version": "2022.3.20f1",
  "capabilities": ["manage_editor", "manage_gameobject", "manage_scene"],
  "ts": 1705500000000
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `protocol_version` | string | Yes | プロトコルバージョン |
| `instance_id` | string | Yes | プロジェクトパス（一意識別子） |
| `project_name` | string | Yes | プロジェクト名（表示用） |
| `unity_version` | string | Yes | Unityバージョン |
| `capabilities` | string[] | No | サポートするコマンド一覧 |

**Response: REGISTERED**

```json
{
  "type": "REGISTERED",
  "success": true,
  "heartbeat_interval_ms": 5000,
  "ts": 1705500000001
}
```

Note: `instance_id`がセッション識別子として機能するため、別途session_idは不要。

**Error Response (REGISTER失敗時):**

```json
{
  "type": "REGISTERED",
  "success": false,
  "error": {
    "code": "PROTOCOL_VERSION_MISMATCH",
    "message": "Unsupported protocol version: 2.0. Expected: 1.0"
  },
  "ts": 1705500000001
}
```

| Error Code | Description |
|------------|-------------|
| `PROTOCOL_VERSION_MISMATCH` | プロトコルバージョン不一致 |
| `INSTANCE_ID_CONFLICT` | 同じinstance_idが既にREADY/BUSY状態で登録済み |

**REGISTER Takeover ルール:**

新しいREGISTERは常に既存接続を**強制切断**して上書きする:

```
1. 同じinstance_idの既存エントリがある場合
2. 既存のTCP接続を強制切断（FINまたはRST）
3. 新しい接続でエントリを上書き
4. REGISTERED返却
```

理由:
- Unityは同一PJを複数開けないため、新しい接続が「正しい」
- ゾンビ接続問題を回避
- INSTANCE_ID_CONFLICTは発生しない（常に上書き）

Note: `INSTANCE_ID_CONFLICT`エラーは将来の拡張用に予約（現仕様では発生しない）

### STATUS

状態変更時に送信。

```json
{
  "type": "STATUS",
  "instance_id": "/Users/dev/MyGame",
  "status": "reloading",
  "detail": "Domain reload started",
  "ts": 1705500000000
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `status` | string | Yes | `ready` \| `busy` \| `reloading` \| `error` |
| `detail` | string | No | 追加情報 |

### COMMAND_RESULT

コマンド実行結果。

```json
{
  "type": "COMMAND_RESULT",
  "id": "req-uuid-xxxx",
  "success": true,
  "data": {
    "isPlaying": true,
    "isCompiling": false
  },
  "ts": 1705500000000
}
```

```json
{
  "type": "COMMAND_RESULT",
  "id": "req-uuid-xxxx",
  "success": false,
  "error": {
    "code": "INVALID_PARAMS",
    "message": "Unknown action: invalid"
  },
  "ts": 1705500000000
}
```

### PONG

Heartbeat応答。PINGの`ts`をそのままエコーバックする（RTT計測用）。

```json
{
  "type": "PONG",
  "ts": 1705500000000,
  "echo_ts": 1705500000000
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ts` | int64 | Yes | PONG送信時のタイムスタンプ |
| `echo_ts` | int64 | Yes | 受信したPINGの`ts`をエコーバック |

---

## Relay → Unity Messages

### PING

Heartbeat要求。

```json
{
  "type": "PING",
  "ts": 1705500000000
}
```

### COMMAND

コマンド実行要求。

```json
{
  "type": "COMMAND",
  "id": "req-uuid-xxxx",
  "command": "manage_editor",
  "params": {
    "action": "play"
  },
  "timeout_ms": 30000,
  "ts": 1705500000000
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | リクエストID (冪等性用) |
| `command` | string | Yes | コマンド名 |
| `params` | object | Yes | パラメータ |
| `timeout_ms` | int | No | タイムアウト (default: 30000) |

---

## CLI → Relay Messages

### REQUEST

コマンド実行要求。

```json
{
  "type": "REQUEST",
  "id": "req-uuid-xxxx",
  "instance": "/Users/dev/MyGame",
  "command": "manage_editor",
  "params": {
    "action": "play"
  },
  "timeout_ms": 30000,
  "ts": 1705500000000
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | リクエストID |
| `instance` | string | No | 対象インスタンス (省略時はデフォルト) |
| `command` | string | Yes | コマンド名 |
| `params` | object | Yes | パラメータ |
| `timeout_ms` | int | No | タイムアウト (default: 30000) |

### LIST_INSTANCES

接続中インスタンス一覧取得。

```json
{
  "type": "LIST_INSTANCES",
  "id": "req-uuid-xxxx",
  "ts": 1705500000000
}
```

### SET_DEFAULT

デフォルトインスタンス設定。

```json
{
  "type": "SET_DEFAULT",
  "id": "req-uuid-xxxx",
  "instance": "/Users/dev/MyGame",
  "ts": 1705500000000
}
```

---

## Relay → CLI Messages

### RESPONSE

リクエスト成功時。

```json
{
  "type": "RESPONSE",
  "id": "req-uuid-xxxx",
  "success": true,
  "data": {
    "isPlaying": true
  },
  "ts": 1705500000000
}
```

### ERROR

リクエスト失敗時。

```json
{
  "type": "ERROR",
  "id": "req-uuid-xxxx",
  "success": false,
  "error": {
    "code": "INSTANCE_NOT_FOUND",
    "message": "Instance '/Users/dev/MyGame' not found"
  },
  "ts": 1705500000000
}
```

**Error Codes:**

| Code | Description |
|------|-------------|
| `INSTANCE_NOT_FOUND` | 指定インスタンスが存在しない |
| `INSTANCE_RELOADING` | インスタンスがリロード中 |
| `INSTANCE_BUSY` | インスタンスがビジー状態 |
| `INSTANCE_DISCONNECTED` | インスタンスが切断されている |
| `COMMAND_NOT_FOUND` | コマンドが存在しない |
| `INVALID_PARAMS` | パラメータが不正 |
| `TIMEOUT` | タイムアウト |
| `INTERNAL_ERROR` | 内部エラー |
| `PROTOCOL_ERROR` | プロトコルエラー |
| `MALFORMED_JSON` | JSON解析エラー |
| `PAYLOAD_TOO_LARGE` | ペイロードサイズ超過 |
| `PROTOCOL_VERSION_MISMATCH` | プロトコルバージョン不一致 |
| `CAPABILITY_NOT_SUPPORTED` | 未サポートのコマンド |
| `QUEUE_FULL` | コマンドキューが満杯 |

### INSTANCES

インスタンス一覧。

```json
{
  "type": "INSTANCES",
  "id": "req-uuid-xxxx",
  "success": true,
  "data": {
    "instances": [
      {
        "instance_id": "/Users/dev/MyGame",
        "project_name": "MyGame",
        "unity_version": "2022.3.20f1",
        "status": "ready",
        "is_default": true
      },
      {
        "instance_id": "/Users/dev/Demo",
        "project_name": "Demo",
        "unity_version": "2021.3.10f1",
        "status": "reloading",
        "is_default": false
      }
    ]
  },
  "ts": 1705500000000
}
```

---

## State Machine

### Unity Instance States

```
                         ┌─────────────────────────────────────┐
                         │                                     │
                         ▼                                     │
    ┌──────────────┐  REGISTER   ┌─────────┐                   │
    │ DISCONNECTED ├────────────→│  READY  │◄──────────────────┤
    └──────────────┘             └────┬────┘                   │
           ▲                         │                         │
           │                         │ COMMAND received        │
           │                         ▼                         │
           │                     ┌───────┐                     │
           │                     │ BUSY  │                     │
           │                     └───┬───┘                     │
           │                         │ COMMAND_RESULT sent     │
           │                         ▼                         │
           │                     ┌───────┐   afterReload       │
           │                     │ READY ├─────────────────────┘
           │                     └───┬───┘
           │                         │ beforeReload
           │                         ▼
           │                   ┌───────────┐
           │                   │ RELOADING │
           │                   └─────┬─────┘
           │                         │
           │   heartbeat timeout     │ connection lost
           │   OR connection lost    │ (during reload)
           └─────────────────────────┴──────────────────────────
```

### BUSY State Handling

BUSY状態で新しいCOMMANDが来た場合:

| 設定 | 挙動 |
|------|------|
| `queue_enabled=true` | キューに追加（最大10件） |
| `queue_enabled=false` | ERROR返却 (code: `INSTANCE_BUSY`) |
| キュー満杯時 | ERROR返却 (code: `QUEUE_FULL`) |

Default: `queue_enabled=false`（シンプルさ優先）

キュー処理順序: **FIFO** (First In, First Out)

### RELOADING中のコマンド処理

RELOADING状態でCOMMANDを受信した場合:

```
1. Relayは即座にERROR返却 (code: INSTANCE_RELOADING)
2. コマンドはキューに入れない（保持しない）
3. CLIがexponential backoffでリトライ
```

理由:
- Relay側の状態がシンプル
- キュー機能はデフォルトOFF
- リトライ戦略はCLI側に委ねる

**In-flightコマンドの扱い:**

BUSY状態でRELOADINGに遷移した場合（beforeAssemblyReload）:

```
1. 実行中コマンドは中断される（Unityプロセスの都合）
2. COMMAND_RESULTは返らない可能性が高い
3. Relayはcommand_timeout_ms後にTIMEOUTをCLIに返却
4. CLIがリトライ
```

**Late COMMAND_RESULTの扱い:**

TIMEOUT返却後に遅れてCOMMAND_RESULTが到着した場合:

```
1. Relayはrequest_idがpending setにあるか確認
2. pending setにない場合 → 破棄（ログ出力のみ）
3. pending setにある場合 → 通常処理（waiting clientに返却）
```

**Queued commandsの扱い:**

queue_enabled=trueでキューにコマンドがある状態でRELOADING/DISCONNECTに遷移した場合:

```
1. キュー内の全コマンドにTIMEOUT（またはINSTANCE_RELOADING）を返却
2. キューをフラッシュ（空にする）
3. CLIがそれぞれリトライ
```

### State Descriptions

| State | Description | Allowed Operations |
|-------|-------------|-------------------|
| `DISCONNECTED` | 未接続 | REGISTER待ち |
| `READY` | コマンド受付可能 | COMMAND受付 |
| `BUSY` | コマンド実行中 | 待機のみ |
| `RELOADING` | ドメインリロード中 | 待機のみ (タイムアウトあり) |

### Transition Rules

1. **DISCONNECTED → READY**: REGISTER成功時
2. **READY → BUSY**: COMMAND受信時
3. **BUSY → READY**: COMMAND_RESULT送信後
4. **READY → RELOADING**: beforeAssemblyReload時 (STATUS "reloading"送信)
5. **RELOADING → READY**: afterAssemblyReload時（下記参照）
6. **ANY → DISCONNECTED**: heartbeatタイムアウト or 接続断

### RELOADING Recovery Flow

ドメインリロード後の復帰手順:

```
[beforeAssemblyReload]
1. Unity: STATUS {status: "reloading"} 送信
2. Unity: TCP接続を維持 or 切断（どちらでも可）

[afterAssemblyReload]
3. Unity: TCP接続が切断されていた場合、再接続
4. Unity: REGISTER 送信（新規接続として扱う）
5. Relay: instance_idが既存なら、状態を引き継ぎREADYに更新
6. Relay: REGISTERED 返信
7. Unity: STATUS {status: "ready"} 送信（オプション、REGISTERで暗黙的にREADY）
```

Note: リロード後は新しいTCP接続になるため、REGISTERを再送信する。
Relayは同じ`instance_id`なら既存エントリを更新（上書き）する。

---

## Heartbeat

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `heartbeat_interval_ms` | 5000 | PING送信間隔 |
| `heartbeat_timeout_ms` | 15000 | 無応答でDISCONNECTED (3回分) |

### Sequence

```
Relay                          Unity
  │                              │
  │  PING {ts: T1}               │
  ├─────────────────────────────→│
  │                              │
  │  PONG {ts: T2, echo_ts: T1}  │
  │←─────────────────────────────┤
  │                              │
  │  (5秒後)                      │
  │  PING {ts: T2}               │
  ├─────────────────────────────→│
  │                              │
```

### Timeout Handling

- 3回連続でPONGが返らない場合、DISCONNECTED扱い
- RELOADING状態では別途 `reload_timeout_ms` (default: 30000) を適用

### Single Outstanding PING

PINGは単一のみ有効:

```
1. Relayは1つのPINGのみ送信
2. PONGを受信するまで次のPINGは送信しない
3. heartbeat_timeout_ms内にPONGが来ない場合、再送（最大3回）
4. 3回連続失敗でDISCONNECTED
```

理由:
- 実装がシンプル
- RTT計測は厳密でなくて良い（死活監視が主目的）

### Heartbeat タイミング詳細

```
┌────────────────────────────────────────────────────────────────────────┐
│ heartbeat_interval_ms = 5000ms (PING送信間隔)                          │
│ heartbeat_timeout_ms = 15000ms (PONG待ちタイムアウト)                   │
│                                                                        │
│ タイムライン:                                                           │
│                                                                        │
│   0s     5s    10s    15s    20s    25s    30s    35s                  │
│   │      │      │      │      │      │      │      │                   │
│   PING─────────────────────────────→ (15s待ち)                         │
│          │      PONG受信 → 次のPING待機                                 │
│          │      ↓                                                      │
│          PING────────────────────→ (15s待ち)                           │
│                                                                        │
│ タイムアウト時:                                                         │
│   PING → 15s待ち → 未応答 → PING再送(1) → 15s待ち → 未応答 →           │
│   PING再送(2) → 15s待ち → 未応答 → DISCONNECTED                        │
│                                                                        │
│ 最大検出時間: 15s × 3 = 45秒                                            │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Domain Reload Handling

### Sequence

```
Unity                          Relay                          CLI
  │                              │                              │
  │ beforeAssemblyReload         │                              │
  │                              │                              │
  │ STATUS {reloading}           │                              │
  ├─────────────────────────────→│                              │
  │                              │ (状態更新)                    │
  │                              │                              │
  │ [connection may drop]        │                              │
  │                              │                              │  REQUEST
  │                              │◄─────────────────────────────┤
  │                              │                              │
  │                              │ ERROR {INSTANCE_RELOADING}   │
  │                              ├─────────────────────────────→│
  │                              │                              │ (リトライ待機)
  │                              │                              │
  │ afterAssemblyReload          │                              │
  │                              │                              │
  │ REGISTER (再接続)             │                              │
  ├─────────────────────────────→│                              │
  │                              │                              │
  │ STATUS {ready}               │                              │
  ├─────────────────────────────→│                              │
  │                              │ (状態更新)                    │
  │                              │                              │  REQUEST (リトライ)
  │                              │◄─────────────────────────────┤
  │                              │                              │
  │ COMMAND                      │                              │
  │◄─────────────────────────────┤                              │
```

### CLI Retry Strategy (Exponential Backoff)

```
リトライ対象エラーコード: INSTANCE_RELOADING, INSTANCE_BUSY, TIMEOUT, INSTANCE_DISCONNECTED
リトライ間隔: 500ms → 1000ms → 2000ms → 4000ms → 8000ms (max)
最大リトライ時間: 30秒
```

```python
def backoff(attempt: int) -> float:
    """Exponential backoff with cap"""
    return min(0.5 * (2 ** attempt), 8.0)  # 500ms〜8000ms
```

---

## Idempotency

リクエストIDによる冪等性保証。

### request_idのスコープ

```
request_id = "{client_id}:{uuid}"

例: "cli-abc123:550e8400-e29b-41d4-a716-446655440000"
```

- **client_id**: CLIプロセス起動時に生成（UUID v4の先頭12文字）
- **uuid**: リクエストごとに生成（UUID v4）
- スコープ: **グローバル**（全インスタンス共通のキャッシュ）

### Relay側の重複排除

```python
class RequestCache:
    """直近N秒のリクエスト結果をキャッシュ"""
    cache: dict[str, Response]  # id -> response (成功のみ)
    pending: set[str]           # in-flight request ids
    ttl_seconds: int = 60

    def handle_request(self, request_id: str, execute_fn) -> Response:
        # 1. キャッシュにあれば返す（成功レスポンスのみ）
        if request_id in self.cache:
            return self.cache[request_id]

        # 2. in-flight中なら待機（同じIDの重複リクエスト）
        if request_id in self.pending:
            return self.wait_for_result(request_id)

        # 3. 新規実行
        self.pending.add(request_id)
        try:
            response = execute_fn()
            # 成功レスポンスのみキャッシュ（TIMEOUT等のエラーはキャッシュしない）
            if response.success:
                self.cache[request_id] = response
            return response
        finally:
            self.pending.discard(request_id)
```

**キャッシュルール:**
- **成功レスポンスのみ**キャッシュする
- エラー（TIMEOUT, INSTANCE_RELOADING等）はキャッシュしない
- リトライ時に実際のコマンド再実行が行われることを保証

### CLI側のリトライ

```python
def send_with_retry(request: Request, max_retries: int = 3) -> Response:
    request_id = request.id  # 同じIDでリトライ（冪等性保証）
    for attempt in range(max_retries):
        try:
            return send(request)
        except TimeoutError:
            if attempt < max_retries - 1:
                sleep(backoff(attempt))
                continue
            raise
```

---

## Commands

### manage_editor

| Action | Description |
|--------|-------------|
| `play` | Play Mode開始 |
| `stop` | Play Mode停止 |
| `pause` | 一時停止 |
| `step` | 1フレーム進める |

### get_editor_state

エディタ状態取得 (Read-only)。

Response:
```json
{
  "isPlaying": false,
  "isPaused": false,
  "isCompiling": false,
  "currentScene": "Assets/Scenes/Main.unity"
}
```

### manage_gameobject

| Action | Description |
|--------|-------------|
| `create` | GameObject作成 |
| `delete` | GameObject削除 |
| `find` | GameObject検索 |
| `get_components` | コンポーネント一覧 |

### manage_scene

| Action | Description |
|--------|-------------|
| `load` | シーン読み込み |
| `save` | シーン保存 |
| `get_hierarchy` | 階層取得 |

---

## Configuration Defaults

全設定値の一覧:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `relay_port` | 6500 | Relay Serverリスンポート |
| `heartbeat_interval_ms` | 5000 | PING送信間隔 |
| `heartbeat_timeout_ms` | 15000 | 無応答でDISCONNECTED (3回分) |
| `reload_timeout_ms` | 30000 | リロード最大待機時間 |
| `command_timeout_ms` | 30000 | コマンド実行タイムアウト |
| `cli_backoff_initial_ms` | 500 | CLIリトライ初期間隔 |
| `cli_backoff_max_ms` | 8000 | CLIリトライ最大間隔 |
| `cli_max_retry_time_ms` | 30000 | CLIリトライ最大時間 |
| `request_cache_ttl_s` | 60 | 冪等性キャッシュTTL |
| `queue_max_size` | 10 | コマンドキュー最大件数 |
| `queue_enabled` | false | キュー機能有効化 |
| `max_payload_bytes` | 16777216 | 最大ペイロード (16MiB) |

---

## Instance ID

`instance_id`はプロジェクトパスをそのまま使用:

```
instance_id = project_path

例: "/Users/dev/MyGame"
```

### 正規化ルール（Unity側で実施）

```csharp
// Unity C#
string instanceId = Path.GetFullPath(Application.dataPath + "/..");
// 結果: "/Users/dev/MyGame" (絶対パス、末尾スラッシュなし)
```

- **絶対パス**に変換（相対パス禁止）
- **シンボリックリンク解決**しない（そのまま）
- **末尾スラッシュ**なし
- **プラットフォーム依存**: Windowsは`\`、macOS/Linuxは`/`
- Relay側は**文字列比較のみ**（正規化しない）

### デフォルトインスタンス

```
- 最初に登録されたインスタンス → デフォルト
- SET_DEFAULTで明示的に変更可能
- インスタンスが1つだけの場合、常にそれがデフォルト
```

### CLI使用例

```bash
# パス補完が効く
$ u --instance /Users/dev/MyGame state
$ u --instance /Users/dev/Demo play

# 省略時はデフォルトインスタンス
$ u state
```

---

## Security Considerations

### Localhost Only (Default)

- Relay Serverは`127.0.0.1`のみにbind
- 外部からのアクセスは拒否

### Optional Token Authentication

将来的な拡張用:

```json
{
  "type": "REGISTER",
  "token": "shared-secret-token",
  ...
}
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-01 | Initial specification |
