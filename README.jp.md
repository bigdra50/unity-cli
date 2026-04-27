# Unity CLI

[![CI](https://github.com/bigdra50/unity-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/bigdra50/unity-cli/actions/workflows/ci.yml)
[![Complexity](https://img.shields.io/badge/complexity-A%2FB-brightgreen)](https://github.com/bigdra50/unity-cli/actions/workflows/ci.yml)
[![Maintainability](https://img.shields.io/badge/maintainability-A-brightgreen)](https://github.com/bigdra50/unity-cli/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey)](https://github.com/bigdra50/unity-cli)
[![Unity](https://img.shields.io/badge/Unity-2022.3%2B-black?logo=unity)](https://unity.com/)
[![openupm](https://img.shields.io/npm/v/com.bigdra50.unity-bridge?label=openupm&registry_uri=https://package.openupm.com)](https://openupm.com/packages/com.bigdra50.unity-bridge/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/bigdra50/unity-cli)

[English](README.md)

コマンドラインから Unity Editor を操作する CLI ツール。

## 概要

Play Mode 制御、コンソールログ取得、テスト実行、シーン/GameObject 操作など、Unity Editor の主要機能を CLI から実行できます。

```bash
# Play Mode 制御
u play
u stop

# コンソールログ取得（エラー以上）
u console get -l E

# メニュー実行
u menu exec "Assets/Refresh"

# ContextMenu 実行
u menu context "DoSomething" -t "/Player"
```

主な特徴:
- Unity Editor の主要操作を CLI で実行
- MenuItem / ContextMenu の実行に対応
- 複数 Unity インスタンスの同時制御
- ドメインリロード耐性（自動再接続）
- UI Toolkit VisualElementツリーの検査・操作（dump, query, inspect, click, scroll, text）
- 動的API呼び出し（`u api call/schema` — 5,243+ Unity静的メソッド対応）
- モンキーテスト（`u uitree monkey`）と構造スナップショット（`u uitree snapshot`）
- プロジェクトを適切なバージョンで開く（Unity Hub連携）
- プロジェクト情報取得（Relay Server不要）

## 動作要件

- [uv](https://docs.astral.sh/uv/) (Python パッケージマネージャー)
- Python 3.11+
- Unity 2022.3+
- Unity Hub（`open`/`editor`コマンド使用時）

## クイックスタート

### 1. Unity側セットアップ

UnityプロジェクトにUnityBridgeパッケージを追加:

```bash
# OpenUPM経由（推奨）
openupm add com.bigdra50.unity-bridge

# または git URL で追加
# Window > Package Manager > + > Add package from git URL...
# https://github.com/bigdra50/unity-cli.git?path=UnityBridge
```

### 2. 接続

Unity Editorで `Window > Unity Bridge` を開き:
1. Start Server をクリック（Relay Server起動）
2. Connect をクリック（Unity → Relay接続）

ツールバー右側のインジケータで接続状態を確認でき、クリックで接続/切断をトグルできます。

### 3. CLIで操作

```bash
# uvx で直接実行（インストール不要）
uvx --from git+https://github.com/bigdra50/unity-cli u state

# Play Mode制御
uvx --from git+https://github.com/bigdra50/unity-cli u play
uvx --from git+https://github.com/bigdra50/unity-cli u stop

# コンソールログ取得（エラー以上）
uvx --from git+https://github.com/bigdra50/unity-cli u console get -l E
```

## インストール

```bash
# グローバルインストール
uv tool install git+https://github.com/bigdra50/unity-cli

# インタラクティブUI付き（エディタ選択プロンプト）
uv tool install "git+https://github.com/bigdra50/unity-cli[interactive]"

# CLIコマンド（すべてのエイリアスが同じ動作）
unity-cli state    # フルネーム
unity state        # 短縮形
u state            # 最短形

u play
u console get -l E | head -10  # 最新10件のエラー以上

# Relay Server 単体起動
unity-relay --port 6500
```

## CLI コマンド

### バージョン

```bash
u version                     # CLIバージョンを表示
```

### シェル補完

```bash
# Zsh
u completion -s zsh > ~/.zsh/completions/_unity-cli

# Bash
u completion -s bash >> ~/.bashrc

# Fish
u completion -s fish > ~/.config/fish/completions/unity-cli.fish

# PowerShell
u completion -s powershell >> $PROFILE
```

### プロジェクトを開く

```bash
# プロジェクトを適切なバージョンで開く（ProjectVersion.txt参照）
u open ./MyUnityProject

# エディタバージョンを指定
u open ./MyUnityProject --editor 2022.3.10f1

# 非インタラクティブモード（CI/スクリプト向け）
u open ./MyUnityProject --non-interactive

# 終了まで待機
u open ./MyUnityProject --wait
```

### エディタ管理

```bash
# インストール済みエディタ一覧
u editor list

# エディタインストール
u editor install 2022.3.10f1

# モジュール付きでインストール
u editor install 2022.3.10f1 --modules android ios webgl

# 非リリース版をchangeset指定でインストール
u editor install 6000.1.0a1 --changeset abc123
```

### プロジェクト情報（Relay Server不要）

```bash
# プロジェクト全情報
u project info ./MyUnityProject

# Unityバージョンのみ
u project version ./MyUnityProject

# パッケージ一覧
u project packages ./MyUnityProject
u project packages ./MyUnityProject --include-modules  # 組み込みモジュールも含める

# タグ・レイヤー
u project tags ./MyUnityProject

# 品質設定
u project quality ./MyUnityProject

# Assembly Definition一覧
u project assemblies ./MyUnityProject

# JSON出力
u --json project info ./MyUnityProject
```

### 基本操作（Relay Server経由）

```bash
# エディタ状態確認
u state

# Play Mode制御
u play
u stop
u pause

# コンソールログ
u console get                  # 全件（プレーンテキスト）
u console get --json           # 全件（JSON形式）
u console get -s               # スタックトレース付き
u console get -l W             # warning以上（warning, error, exception）
u console get -l E             # error以上（error, exception）
u console get -l +W            # warningのみ
u console get -l +E+X          # errorとexceptionのみ
u console get | head -20       # 最新20件
u console get | grep "error"   # テキストでフィルタ
u console clear                # コンソールクリア

# アセットリフレッシュ
u refresh

# エディタ選択状態
u selection

# スクリーンショット（デフォルトは capture、--burst で burst モード）
u screenshot                           # GameView（デフォルト）
u screenshot -s scene                  # SceneView
u screenshot -s camera                 # Camera.Render
u screenshot -p ./output.png           # 出力パス指定
u screenshot --super-size 2            # 2倍解像度（game only）
u screenshot -s camera -c "Main Camera" -W 1920 -H 1080
u screenshot --burst -n 10             # Burst: 10フレーム連続撮影
u screenshot --burst -n 5 -f jpg -q 80 # Burst + フォーマット/品質指定

# パイプ時はパスのみ出力
u screenshot -s game | mcat -i   # ターミナルにインライン表示
u screenshot -s game | pbcopy    # パスをクリップボードにコピー
u screenshot -s game | xargs open  # デフォルトビューアで開く
```

### インスタンス管理

```bash
# 接続中インスタンス一覧
u instances

# 特定インスタンスを指定
u --instance /Users/dev/MyGame state
u --instance /Users/dev/Demo play
```

### テスト実行

```bash
# EditModeテスト
u tests run edit

# PlayModeテスト
u tests run play

# フィルタリング
u tests run edit --test-names "MyTests.SampleTest"
u tests run edit --group-pattern ".*Integration.*"
u tests run edit --categories "Unit" "Integration"
u tests run edit --assemblies "MyGame.Tests"

# 結果を待たず即時リターン
u tests run edit --no-wait

# テスト一覧
u tests list edit
u tests list play

# 実行中テストのステータス確認
u tests status
```

### シーン操作

```bash
# アクティブシーン情報
u scene active

# 階層取得
u scene hierarchy                    # ルートのみ（depth 1）
u scene hierarchy --depth 2          # 2階層まで
u scene hierarchy --page-size 100    # ページサイズ指定

# シーン操作
u scene load --name MainScene
u scene load --path "Assets/Scenes/Sub.unity" --additive
u scene save
u scene save --path "Assets/Scenes/NewScene.unity"
```

### GameObject操作

```bash
# 検索
u gameobject find "Main Camera"
u gameobject find "Player" --iterate-all

# 作成
u gameobject create --name "MyCube" --primitive Cube --position 0 1 0

# 変更
u gameobject modify --name "MyCube" --position 5 0 0 --rotation 0 45 0

# 削除
u gameobject delete --name "MyCube"
```

### コンポーネント操作

```bash
# コンポーネント一覧
u component list -t "Main Camera"

# コンポーネント詳細
u component inspect -t "Main Camera" -T Camera

# コンポーネント追加
u component add -t "Player" -T Rigidbody

# コンポーネント削除
u component remove -t "Player" -T Rigidbody
```

### メニュー/ContextMenu

```bash
# メニュー実行
u menu exec "Edit/Play"
u menu exec "Assets/Refresh"
u menu exec "Window/General/Console"

# メニュー一覧
u menu list                    # 全メニュー
u menu list -f "Assets"        # フィルタリング
u menu list -f "Play" -l 20    # 件数制限

# ContextMenu実行（シーン内オブジェクト）
u menu context "Reset" -t "/Player"

# ContextMenu実行（ScriptableObject）
u menu context "DoSomething" -t "Assets/Data/Config.asset"

# ContextMenu実行（Prefab）
u menu context "Initialize" -t "Assets/Prefabs/Enemy.prefab"
```

### アセット操作

```bash
# Prefab作成
u asset prefab -s "Player" -p "Assets/Prefabs/Player.prefab"

# ScriptableObject作成
u asset scriptable-object -T "GameConfig" -p "Assets/Data/Config.asset"

# アセット情報
u asset info "Assets/Data/Config.asset"
```

### UI Toolkit ツリー検査・操作

UI Toolkit VisualElementツリーの検査と操作。ref IDで要素を指定する。

```bash
# パネル一覧 / ツリーダンプ
u uitree dump
u uitree dump -p "PanelSettings" --json

# 要素検索（AND条件）
u uitree query -p "PanelSettings" -c "action-btn"

# 詳細取得
u uitree inspect ref_3 --style --children

# 操作
u uitree click -p "PanelSettings" -n "BtnStart"
u uitree text -p "PanelSettings" -n "ScoreLabel"
u uitree scroll -p "PanelSettings" -n "ScrollView" --y 500

# モンキーテスト（ランダム操作 + エラー監視）
u uitree monkey -p "PanelSettings" -c "action-btn" --count 50 --seed 42

# 構造スナップショット（save/diff/list/delete）
u uitree snapshot save -p "PanelSettings" --name baseline
u uitree snapshot diff -p "PanelSettings" --name baseline
```

### 動的API呼び出し

リフレクション経由で任意の Unity public static メソッドを呼び出す。5,243+ メソッド対応。

```bash
# メソッド検索
u api schema --type AssetDatabase
u api schema --namespace UnityEditor --limit 20

# メソッド呼び出し
u api call UnityEngine.Application get_unityVersion
u api call UnityEditor.AssetDatabase Refresh
u api call UnityEditor.EditorApplication ExecuteMenuItem --params '["Window/General/Console"]'

# オフラインスキーマ（Unityバージョンごとにキャッシュ）
u api schema --offline --type PlayerSettings
```

### フレーム記録

```bash
# 記録開始（カメラベース、FPS/フォーマット/解像度を指定可能）
u recorder start --fps 30 -f jpg -q 80
u recorder start --fps 60 -W 1920 -H 1080 -o ./frames

# 記録停止と結果取得
u recorder stop

# 記録ステータス確認
u recorder status
```

### 設定

```bash
# 現在の設定を表示
u config show

# デフォルト .unity-cli.toml を生成
u config init
u config init -o ./custom-config.toml
u config init --force                  # 既存を上書き
```

## オプション

### 共通オプション

| オプション | 説明 | デフォルト |
|-----------|------|-----------|
| `--relay-host` | Relay Serverホスト | 127.0.0.1 |
| `--relay-port` | Relay Serverポート | 6500 |
| `--instance`, `-i` | 対象Unityインスタンス | デフォルト |
| `--timeout`, `-t` | タイムアウト（秒） | 10.0 |
| `--json`, `-j` | JSON形式で出力 | false |
| `--quiet`, `-q` | 成功メッセージを抑制 | false |
| `--verbose` | リクエスト/レスポンスをstderrに出力 | false |

### tests専用オプション

| オプション | 説明 |
|-----------|------|
| `--test-names`, `-n` | テスト名（完全一致） |
| `--group-pattern`, `-g` | テスト名の正規表現パターン |
| `--categories`, `-c` | NUnitカテゴリ |
| `--assemblies`, `-a` | アセンブリ名 |
| `--no-wait` | 結果を待たず即時リターン |

### scene hierarchy オプション

| オプション | 説明 | デフォルト |
|-----------|------|-----------|
| `--depth`, `-d` | 階層の深さ | 1（ルートのみ） |
| `--page-size` | ページサイズ | 50 |
| `--cursor` | ページネーションカーソル | 0 |

## 終了コード

| コード | 名前 | 説明 |
|--------|------|------|
| 0 | SUCCESS | コマンド成功 |
| 1 | USAGE_ERROR | 不正な引数、バリデーション失敗 |
| 2 | TRANSIENT_ERROR | リトライ可能: リロード中、ビジー、タイムアウト |
| 3 | CONNECTION_ERROR | Relay Server未起動・接続不可 |
| 4 | OPERATION_ERROR | コマンド失敗（インスタンス未検出、プロトコルエラー等） |
| 5 | TEST_FAILURE | テスト実行は完了したが一部失敗 |

```bash
u state; echo $?              # 0 = 接続中, 3 = relay未起動
u tests run edit; echo $?     # 0 = 全通過, 5 = 一部失敗
u play --quiet 2>/dev/null; echo $?  # 出力抑制、終了コードのみ確認
```

## 環境変数

| 変数 | 説明 |
|------|------|
| `UNITY_CLI_QUIET` | `1` で成功メッセージを抑制 |
| `UNITY_CLI_VERBOSE` | `1` でリクエスト/レスポンスをstderrに出力 |
| `UNITY_CLI_JSON` | `1` でデフォルトJSON出力 |
| `UNITY_CLI_NO_PRETTY` | `1` でRich装飾を無効化 |
| `NO_COLOR` | 設定でカラーを無効化（標準） |

## AI Agent Skills

AIコーディングエージェント向けワークフロースキル（Claude Code, Codex, Gemini CLI, Cursor, GitHub Copilot, Windsurf 等対応）。[agentskills.io](https://agentskills.io/specification) 仕様準拠。

### Option 1: GitHub CLI（推奨, gh 2.90.0+）

```bash
# 対話: スキル一覧から選択
gh skill install bigdra50/unity-cli

# 単体インストール
gh skill install bigdra50/unity-cli unity-verify

# 全スキル一括（Claude Code, ユーザースコープ）
for s in unity-shared unity-verify unity-debug unity-build \
         unity-scene unity-asset unity-perf unity-ui unity-api; do
  gh skill install bigdra50/unity-cli "$s" --agent claude-code --scope user
done

# 特定リリースに固定
gh skill install bigdra50/unity-cli unity-verify --pin v3.11.0
```

`--agent` で 40+ エージェントに対応 (claude-code, github-copilot, cursor, codex, gemini-cli, ...)。デフォルトは `--scope project`。グローバルは `--scope user`。

### Option 2: Skills CLI（クロスエージェント, gh 不要）

```bash
# 全スキルインストール（プロジェクトローカル）
npx skills add github:bigdra50/unity-cli

# グローバルインストール（ユーザーレベル）
npx skills add github:bigdra50/unity-cli -g

# 特定スキルのみ
npx skills add github:bigdra50/unity-cli -s unity-ui unity-api
```

詳細は [Skills CLI](https://skills.sh/) を参照。

### Option 3: 手動（git clone）

```bash
git clone https://github.com/bigdra50/unity-cli.git

# 単体
cp -r unity-cli/skills/unity-verify ~/.claude/skills/

# 全スキル
cp -r unity-cli/skills/* ~/.claude/skills/
```

### スキル一覧

| スキル | 内容 |
|-------|------|
| `unity-verify` | コンパイル・テスト検証（refresh → エラー確認） |
| `unity-debug` | エラー調査 |
| `unity-build` | ビルドパイプライン |
| `unity-scene` | シーン構築 |
| `unity-asset` | アセット・依存関係管理 |
| `unity-perf` | プロファイラ分析 |
| `unity-ui` | UIテスト（uitree + monkey + snapshot → PlayMode） |
| `unity-api` | 動的API呼び出し（5,243+ メソッド） |
| `unity-shared` | 共通ルール（他スキルから自動ロード） |

## Recipes

パイプ、スクリプト、ツール連携の例は [docs/recipes.md](docs/recipes.md) を参照。

```bash
u screenshot -s game | mcat -i         # ターミナルにインライン表示
u console get -l E | head -10                  # エラー直近10件
u instances --json | jq -r '.[].instance_id'   # パス抽出
```

## アーキテクチャ

```mermaid
flowchart TB
    subgraph CLI["u (Python)"]
        direction TB
        RC[RelayConnection: TCP通信]
        EB[Exponential Backoff: 500ms → 8s]
        RID[request_id: 冪等性保証]
    end

    subgraph Relay["Relay Server (Python)"]
        direction TB
        IR[InstanceRegistry: 複数Unity管理]
        Cache[RequestCache: 冪等性キャッシュ]
        HB[Heartbeat: Single Outstanding PING]
        Q[Queue: FIFO max 10]
    end

    subgraph Unity["UnityBridge (C#)"]
        direction TB
        Client[RelayClient: 接続管理]
        Dispatcher[CommandDispatcher: BridgeTool属性]
        Reload[BridgeReloadHandler: 再接続]
    end

    CLI -->|TCP:6500| Relay
    Relay -->|TCP:6500| Unity
```

## プロトコル仕様

詳細は [docs/protocol-spec.md](docs/protocol-spec.md) を参照。

- Framing: 4-byte big-endian length + JSON
- State Machine: DISCONNECTED → READY → BUSY → RELOADING
- Heartbeat: 5秒間隔、15秒タイムアウト（3回リトライ）
- Retry: Exponential Backoff（500ms → 8s、最大30秒）

## トラブルシューティング

```bash
# Relay Serverが起動しているか確認
lsof -i :6500                  # macOS / Linux
netstat -ano | findstr :6500   # Windows

# 接続中インスタンス確認
u instances

# Unityコンソールでエラー確認
u console get -l E
```

## v2.x → v3.0 マイグレーション

| 変更点 | v2.x | v3.0 |
|--------|------|------|
| コマンド名 | `unity-mcp` | `unity-cli` |
| 接続先 | Unity直接 (6400) | Relay Server (6500) |
| プロトコル | 8-byte framing | 4-byte framing |
| 複数インスタンス | 非対応 | 対応 |

```bash
# v2.x
unity-mcp --port 6400 state

# v3.0
u state  # Relay経由
u --instance /path/to/project state  # 特定インスタンス
```

## ライセンス

MIT License
