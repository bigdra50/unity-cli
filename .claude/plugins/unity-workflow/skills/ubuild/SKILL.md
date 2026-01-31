---
name: ubuild
description: |
  Unityビルドパイプラインワークフロー。ビルド実行、プラットフォーム設定確認、ビルドエラー対応を行う。
  Use for: "ビルド", "ビルド実行", "build", "ビルド設定", "プラットフォーム"
user-invocable: true
---

# Unity Build Pipeline Workflow

ビルド設定確認・ビルド実行・エラー対応を一連で行うワークフロー。

## CLI Setup

```bash
# グローバルインストール済みの場合
u <command>

# uvx 経由（インストール不要）
uvx --from git+https://github.com/bigdra50/unity-cli u <command>
```

以下のワークフロー内では `u` コマンドを使用する。

## Decision Criteria

| 状況 | フロー |
|------|--------|
| 現在のビルド設定を確認したい | Pre-Build Check Flow → settings 確認 |
| ビルドシーンを確認・変更したい | Pre-Build Check Flow → scenes 確認 |
| 現在の設定でビルドしたい | Pre-Build Check → Build Flow |
| プラットフォームを変更してビルド | Pre-Build Check → Build Flow (--target 指定) |
| ビルドエラーを解決したい | Build Flow → Error Handling |
| ビルドが成功するか事前確認したい | Pre-Build Check Flow のみ |

## Pre-Build Check Flow

```
Request (ビルド実行 or 設定確認)
  │
  ▼
┌─────────────────────────────┐
│ Step 1: Refresh & Compile   │
│ u refresh                   │
│ u state (poll until         │
│   isCompiling == false)     │
└──────────┬──────────────────┘
           ▼
┌─────────────────────────────┐
│ Step 2: Compile Error Check │
│ u console get -l E          │
└──────────┬──────────────────┘
           ▼
      errors? ──yes──► Fix & goto Step 1 (max 3 rounds)
           │              └► 解決しない場合はユーザーに報告
           no
           ▼
┌─────────────────────────────┐
│ Step 3: Build Settings      │
│ u build settings            │
└──────────┬──────────────────┘
           ▼
┌─────────────────────────────┐
│ Step 4: Build Scenes        │
│ u build scenes              │
└──────────┬──────────────────┘
           ▼
      Ready for Build
```

### Step 1: Refresh & Compile Wait

```bash
u refresh
```

refresh 後、コンパイル完了を待つ:

```bash
u state
# isCompiling が true の間、2秒間隔でポーリング
# 最大30秒待機。超えたらタイムアウトとして報告
```

### Step 2: Compile Error Check

```bash
u console get -l E
```

- エラーが0件なら Step 3 へ
- エラーがあればファイル・行番号を特定して修正 → Step 1 に戻る
- 3回修正しても解決しない場合はユーザーに報告

### Step 3: Build Settings 確認

```bash
u build settings
```

確認項目:
- activeTarget: 現在のビルドターゲット
- outputPath: 出力先パス
- developmentBuild: Development Build フラグ
- scriptingBackend: IL2CPP / Mono

ユーザーの指定プラットフォームと異なる場合は警告する。

### Step 4: Build Scenes 確認

```bash
u build scenes
```

- シーンが0件の場合はビルド不可として報告
- 想定外のシーンが含まれていればユーザーに確認

## Build Flow

```
Pre-Build Check 完了
  │
  ▼
┌─────────────────────────────┐
│ Step 5: Build Run           │
│ u build run [options]       │
└──────────┬──────────────────┘
           ▼
      success? ──no──► Error Handling
           │
           yes
           ▼
      Report Results
```

### Step 5: Build Run

基本のビルド:

```bash
u build run
```

プラットフォーム・出力先を指定:

```bash
u build run --target StandaloneWindows64 --output ./Builds/Win
```

シーンを明示指定:

```bash
u build run --scene Assets/Scenes/Main.unity --scene Assets/Scenes/Menu.unity
```

複数オプションの組み合わせ:

```bash
u build run --target Android --output ./Builds/Android --scene Assets/Scenes/Main.unity
```

### Error Handling

ビルド失敗時の対応手順:

```
Build Failed
  │
  ▼
┌─────────────────────────────┐
│ u console get -l E -c 10    │
│ (直近10件のエラーを取得)    │
└──────────┬──────────────────┘
           ▼
      エラー種別を判定
           │
           ├── コンパイルエラー → ソース修正 → Pre-Build Check からやり直し
           ├── Missing Reference → アセット参照を修正
           ├── Shader エラー → シェーダーコードを修正
           └── プラットフォーム依存 → 設定変更を提案
```

よくあるビルドエラー:

| エラーパターン | 原因 | 対処 |
|----------------|------|------|
| `CS0246` / `CS0234` | 名前空間・型が見つからない | using ディレクティブ追加、asmdef 依存追加 |
| `Missing Prefab` | Prefab 参照切れ | アセット再割り当て |
| `Shader error` | シェーダーコンパイルエラー | プラットフォーム対応を確認 |
| `BuildFailedException` | スクリプト内のビルド処理エラー | IPreprocessBuildWithReport 等を確認 |
| `Unsupported API` | プラットフォーム非対応API | #if ディレクティブで分岐 |

## Platform Reference

| BuildTarget | 用途 | 備考 |
|-------------|------|------|
| `StandaloneWindows64` | Windows 64bit | デフォルトの開発ターゲットになりやすい |
| `StandaloneOSX` | macOS | Apple Silicon / Intel の対応に注意 |
| `Android` | Android | SDK/NDK パスの設定が必要 |
| `iOS` | iOS | Xcode プロジェクトを出力。macOS 上でのみ実行可 |
| `WebGL` | ブラウザ | ビルド時間が長い。例外処理やスレッドに制約あり |

## Anti-Patterns

| NG | 理由 | 対策 |
|----|------|------|
| コンパイルエラーを未解決のままビルド実行 | ビルドが必ず失敗し時間を浪費 | Pre-Build Check で事前に解消 |
| 出力先パスを確認せず上書き | 既存ビルドを破壊 | `build settings` で outputPath を確認 |
| シーン確認なしでビルド | 想定外のシーンが含まれる | `build scenes` で事前確認 |
| エラー全件取得 | ログが膨大でトークン浪費 | `-c 10` で件数を絞る |
| ビルド失敗時に即リトライ | 同じエラーで再度失敗 | エラー内容を確認してから対処 |

## Token-Saving Strategies

| 状況 | 対応 |
|------|------|
| エラーが大量 | `-c 10` で最初の10件に絞る |
| 同一エラーの繰り返し | 最初の1件を修正後、再検証 |
| ビルドログが長い | `-l E` でエラーのみ取得 |
| 設定確認のみ | `build settings` と `build scenes` だけ実行し、ビルドは行わない |

## Result Report Format

```
## Build Result

- Target: StandaloneWindows64
- Output: ./Builds/Win
- Scenes: 3
- Result: OK / NG
- Errors: 0 (or error summary)
- Pre-Build Fix Rounds: N/3 used
```

## Related Skills

| スキル | 関係 |
|--------|------|
| uverify | ビルド前のコンパイル検証・テスト実行 |
