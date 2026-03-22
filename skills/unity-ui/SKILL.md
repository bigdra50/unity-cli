---
name: unity-ui
description: |
  UI 開発・検査・自動テストワークフロー。uitree で構造把握→CLI E2Eで動作確認→PlayModeテストに移植。
  Use for: "UI確認", "UI Toolkit", "uGUI", "E2Eテスト", "UI操作", "uitree", "スクリーンショット"
user-invocable: true
metadata:
  openclaw:
    category: "game-development"
    requires:
      bins: ["u"]
---

# unity-ui

> **PREREQUISITE:** `../unity-shared/SKILL.md`

> uitree コマンドは Play Mode 中のみ動作する。必ず `u play` してから実行すること。

## UI テストの種別

| 種別 | 検証内容 | 手法 | スクショ |
|------|---------|------|---------|
| Functional | 操作→状態が正しいか | click → text で値検証 | 不要 |
| Visual Regression | 外観が変わっていないか | screenshot → 画像比較 | 必要 |
| Structural Snapshot | ツリー構造が変わっていないか | dump --json → diff | 不要 |
| Smoke | 最低限動くか | click → console にエラーなし | 任意 |

## UI システム判定

| 手がかり | UI Toolkit | uGUI |
|---------|-----------|------|
| ファイル | `.uxml`, `.uss` | `.prefab` に Canvas |
| コンポーネント | UIDocument | Canvas, RectTransform |

## コマンドリファレンス

要素の指定方法は2通り: ref ID (`ref_3`) または `-p <panel> -n <name>`。

### 構造把握

```bash
u uitree dump                           # 全パネル一覧
u uitree dump -p "PanelSettings"        # パネルのツリー (各要素の ref/name/type/classes が見える)
u uitree dump -p "PanelSettings" --json # JSON 出力 (snapshot用)
u uitree query -p "PanelSettings" -t Button              # type で検索 (VisualElement ベースのボタンはヒットしない → -c で検索)
u uitree query -p "PanelSettings" -n "BtnStart"          # name で検索
u uitree query -p "PanelSettings" -c "action-btn"        # USS class で検索
u uitree query -p "PanelSettings" -t Button -c "primary" # AND 条件
u uitree inspect -p "PanelSettings" -n "BtnStart"        # 要素詳細
u uitree inspect ref_5_48                                # ref ID で指定
u uitree inspect ref_5_48 --style                        # resolvedStyle 含む
u uitree inspect ref_5_48 --children                     # 子要素情報含む
```

### テキスト取得

```bash
u uitree text -p "PanelSettings" -n "ToastMessage"  # name で指定
u uitree text ref_5_12                               # ref ID で指定
```

### 操作

```bash
u uitree click -p "PanelSettings" -n "BtnContinue"  # name で指定
u uitree click ref_5_48                              # ref ID で指定
u uitree click ref_5_48 --count 2                    # ダブルクリック
u uitree click ref_5_48 --button 1                   # 右クリック
u uitree scroll -p "PanelSettings" -n "ScrollArea" --delta 100
```

### スクリーンショット

```bash
u screenshot                          # GameView (-s game がデフォルト)
u screenshot -p "ui-check.png"        # 保存先指定
u screenshot --burst -n 5             # 連続 (アニメーション確認)
```

UI Toolkit / uGUI (Screen Space) は `-s game` でのみ映る。`-s camera` では映らない。

GameView のキャプチャにはエディタのフォーカスが必要。タイムアウトする場合は再試行で解決することが多い。

### uGUI の場合

uitree は UI Toolkit 専用。uGUI は scene/component コマンドで操作する。

```bash
u scene hierarchy --depth 3
u component list -t "Canvas"
u component inspect -t "MyButton" -T "UnityEngine.UI.Button"
```

## 開発→テストフロー

```
Phase 1: 作成 & 確認
  コード変更 → /unity-verify → play → dump → 操作 → screenshot → stop

Phase 2: CLI E2E テスト
  play → dump で構造把握 → シナリオをスクリプト化 → 繰り返し実行

Phase 3: PlayMode テスト移植
  安定したシナリオを C# に書き直す → CI で回帰テスト
```

### Phase 1: 作成 & 確認

```bash
# 1. コード変更後に検証
# /unity-verify Quick Verify

# 2. Play Mode で UI 確認
u play
u uitree dump -p "PanelSettings"                 # 構造把握
u uitree click -p "PanelSettings" -n "BtnStart"  # 操作
u uitree text -p "PanelSettings" -n "StatusLabel" # 状態確認
u screenshot                                      # 結果キャプチャ
u stop
```

### Phase 2: CLI E2E テスト

Play Mode に入り、dump で構造を把握してから操作シナリオをスクリプト化する。

Functional テスト (値検証):
```bash
u play
u uitree click -p "PanelSettings" -n "BtnContinue"
u uitree text -p "PanelSettings" -n "ToastMessage"
# → 期待値 "Loading save data..." と比較
u console get -l E  # 出力なし = エラーなし
u stop
```

Structural Snapshot (ツリー構造の差分検出):
```bash
u play
u uitree dump -p "PanelSettings" --json > snapshot-current.json
# 前回の snapshot と diff して構造変化を検出
u stop
```

Smoke + Visual:
```bash
u play
u uitree click -p "PanelSettings" -n "BtnStart"
u screenshot -p "after-start.png"
u uitree click -p "PanelSettings" -n "BtnSettings"
u screenshot -p "settings-open.png"
u console get -l E  # エラーなし確認
u stop
```

AI エージェントの自律操作:
```
play → dump → 構造理解 → click → text/screenshot → 結果判定 → 次の操作 → stop
```

### Phase 3: PlayMode テスト移植

CLI E2E で確認したシナリオを C# PlayMode テストに書き直す。

CLI E2E のまま残す:
- 探索的テスト (シナリオが毎回変わる)
- AI エージェントの自律テスト

PlayMode に移植する:
- CI で毎回回す回帰テスト
- フレーム精度が必要 (アニメーション完了待ち等)
- Assert で厳密に状態検証
- InputSystem / EventSystem 経由の操作

移植後は `u tests run play` で実行。

## CLI 非対応操作

unity-shared のフォールバック順に従う:
1. `u api schema --type <Type>` で対応メソッドを検索
2. `u api call` で実行
