# unity-cli Skills 設計計画

rust-skills の設計パターンを参考に、unity-cli の skills を再設計する。

## 設計コンセプト

**unity-cli の役割**: ユーザーの既存ワークフローを補完するツール

```
ユーザーのプロジェクト
├── .claude/
│   ├── rules/               # ユーザー独自のルール
│   │   ├── coding.md        # コーディング標準
│   │   ├── testing.md       # テスト方針
│   │   └── ...              # プロジェクト固有ルール
│   └── plugins/
│       └── unity-cli/       # ← unity-cli を組み込み
│           ├── skills/      # ワークフロー支援
│           └── agents/      # ドキュメント参照支援
```

**責務分離**:
| 責務 | 担当 |
|------|------|
| コーディング標準、テスト方針 | ユーザーの rules |
| ワークフロー支援 (build, debug, etc.) | unity-cli skills |
| ドキュメント・ソース参照 | unity-cli agents |
| プロジェクト固有制約 (VR/XR, Netcode等) | ユーザーが追加 |

## 参考プロジェクト

### rust-skills の設計パターン
- 3層構造: L1 (Language Mechanics) / L2 (Design) / L3 (Domain)
- 集中ルーター: rust-router で質問を適切なスキルへ振り分け
- 38個の専門スキル、8個のエージェント

### nowsprinting/claude-code-settings-for-unity
- ユーザーが構築する rules の参考例
- ドキュメント参照パターン (agents に活用)
- unity-cli が提供するものではなく、共存する対象

## unity-cli の現状

### 既存スキル (7個) - ワークフローとして機能済み

| スキル | 用途 | 主要機能 |
|--------|------|---------|
| build | ビルドパイプライン | Refresh→Compile→Build実行 |
| preflight | コード検証 | Refresh→Compile→EditModeTest→RuntimeCheck |
| debug | エラー調査 | ErrorCapture→Classification→ContextGathering |
| scene | シーン構築 | GameObject配置→Component設定→Prefab化 |
| asset | アセット管理 | 依存関係調査→参照確認→問題検出 |
| ui | UI Toolkit | VisualElement検査→開発イテレーション |
| perf | パフォーマンス | Profiler実行→フレームデータ取得→分析 |

※ unity-csharp は削除（コーディング規約はユーザーの rules/ で定義）

### unity-cli の強み
- TCP リレーサーバー経由で Unity エディタを直接操作
- 複数 Unity インスタンスの同時制御
- ドメインリロード耐性（自動再接続）
- 既存スキルが実際のコマンド実行をガイド

### 現状の課題
- フラット構造（ルーターなし）
- Hook による自動トリガーなし
- エージェント（ドキュメント参照）なし

## アーキテクチャ

```
ユーザー質問
     │
     ▼
┌──────────────────────────────┐
│ Hook層 (キーワード検出)       │  ← 自動トリガー
└──────────────────────────────┘
     │
     ▼
┌──────────────────────────────┐
│ unity-router (振り分け)       │  ← 玄関
└──────────────────────────────┘
     │
     ├─────────────────┬─────────────────┐
     ▼                 ▼                 ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ Layer 1     │ │ Layer 2     │ │ Layer 3     │
│ API操作     │ │ ワークフロー │ │ ドメイン    │
│ (HOW)       │ │ (WHAT)      │ │ (WHY)       │
└─────────────┘ └─────────────┘ └─────────────┘
     │
     ▼
┌──────────────────────────────┐
│ Agents (バックグラウンド調査) │
└──────────────────────────────┘
```

### 各レイヤーの責務

| Layer | 責務 | 問い | 方向 |
|-------|------|------|------|
| Layer 1 (a0X) | API操作 | どうやって実装する？ | ↑ 設計へ遡る |
| Layer 2 (w0X) | ワークフロー | 何をする？ | ↕ 双方向 |
| Layer 3 (domain-*) | ドメイン制約 | なぜその制約？ | ↓ 実装へ降りる |

### プロジェクト固有の規約との競合について

このプラグインは加算的に動作するため、競合リスクは低い設計。

**競合が起きにくい理由**:
1. Hook は検出のみ: unity-router をトリガーするだけで、ユーザー設定を上書きしない
2. スキルは知識ベース: コード生成規約ではなく、判断材料を提供
3. 設定優先度が明確: `settings.local.json > settings.json > plugin.json > CLAUDE.md推奨値`

**結論**: プロジェクト固有の rules や設定がある場合、そちらが優先される。
unity-cli は「情報源」として機能し、最終判断はユーザー/プロジェクト設定に従う。

## 設計方針

### Phase 0: Hook 層追加
Unity 関連キーワードを検出し、unity-router を自動トリガー。

参考: rust-skills の hooks/ 構造

```
hooks/
└── hooks.json                    # トリガー設定
.claude/hooks/
└── unity-skill-eval-hook.sh      # meta-cognition 指令出力
```

#### hooks.json 構造

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "(?i)(...Unity キーワード正規表現...)",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/.claude/hooks/unity-skill-eval-hook.sh"
          }
        ]
      }
    ]
  }
}
```

#### キーワードパターン設計 (100+ パターン)

| カテゴリ | パターン例 | 目的 |
|---------|-----------|------|
| Unity 基本 | `Unity`, `UnityEngine`, `UnityEditor` | コンテキスト検出 |
| コア API | `MonoBehaviour`, `ScriptableObject`, `GameObject`, `Component`, `Transform` | API 質問検出 |
| ファイル拡張子 | `\.unity\b`, `\.prefab\b`, `\.asset\b`, `\.meta\b` | アセット操作検出 |
| エラーコード | `CS\d{4}` | C# エラー全般 |
| UI | `Canvas`, `uGUI`, `UI Toolkit`, `UXML`, `USS`, `VisualElement`, `IMGUI` | UI ドメイン検出 |
| ビルド | `BuildPipeline`, `PlayerSettings`, `BuildTarget`, `AssetBundle` | ビルド質問検出 |
| テスト | `EditMode`, `PlayMode`, `TestRunner`, `NUnit`, `UnityTest` | テスト質問検出 |
| パッケージ | `UPM`, `package\.json`, `manifest\.json`, `PackageManager` | パッケージ質問検出 |
| シリアライズ | `SerializeField`, `SerializeReference`, `JsonUtility` | シリアライズ質問検出 |
| エディタ拡張 | `EditorWindow`, `Inspector`, `PropertyDrawer`, `CustomEditor` | エディタ拡張検出 |
| 質問パターン | `how to`, `why`, `what is`, `best practice` | 意図検出 |
| 日本語 | `どうやって`, `なぜ`, `ベストプラクティス`, `エラー` | 日本語サポート |

#### unity-skill-eval-hook.sh 出力内容

```markdown
=== UNITY SKILLS META-COGNITION ROUTING ===

STEP 1: IDENTIFY ENTRY LAYER + DOMAIN
- Layer 1 シグナル: CS0029, NullReferenceException, MissingReferenceException
- Layer 2 シグナル: build, test, debug, scene, asset, ui, perf
- Layer 3 シグナル: (ユーザー定義ドメイン)

STEP 2: EXECUTE SKILL LOADING
- Layer 識別に基づき適切な Skill を読み込む
- 複数 Layer にまたがる場合は複数 Skill を読み込む

STEP 3: EXECUTE AGENT IF NEEDED
- API 詳細が必要 → unity-guide agent
- バージョン情報が必要 → version-checker agent

STEP 4: OUTPUT FORMAT
### Layer Analysis
- Layer 1 (API): [識別された API 操作]
- Layer 2 (Workflow): [識別されたワークフロー]

### Recommended Approach
- [具体的なアプローチ]
- [参照ドキュメント URL]
```

### Phase 1: unity-router 追加
集中ルーティングスキルを追加し、質問タイプに応じた振り分けを実装。

### Phase 2: 層構造の導入
既存スキルを Layer 2 (Workflow) として再配置し、Layer 1 を追加。

**注意**: Layer 3 (Domain) はプロジェクト固有の要件（VR/XR, Netcode, Photon等）に依存するため、
本計画では含めない。必要に応じてプロジェクトごとに追加する。

```
Layer 2: Workflow (WHAT) - 既存スキル（そのまま活用）
├── build              # ビルドパイプライン
├── scene              # シーン構築 (YAML直接編集フォールバック付き)
├── debug              # エラー調査
├── preflight             # コード検証（コンパイル・テスト）
├── perf               # パフォーマンス最適化
├── ui                 # UI Toolkit ※uGUI 対応を追加検討
└── asset              # アセット管理 (YAML直接編集フォールバック付き)

Layer 3: Domain (プロジェクト固有 - ユーザーが追加)
└── (ユーザーがプロジェクトの .claude/plugins/ に追加)

Layer 1: なし（削除）
└── unity-csharp は削除（プロジェクト固有規約とコンフリクトするため）
    → コーディング規約はユーザーが自身の rules/ で定義
```

#### YAML 直接編集フォールバック

scene、asset スキルは以下の方針で YAML を扱う:

1. 通常は unity-cli 経由で Unity エディタを操作
2. unity-cli が対応していない操作の場合は YAML を直接編集
3. YAML 編集時は unity-guide エージェントで公式ドキュメントを参照

対象ファイル:
- `.meta`: アセットメタデータ
- `.asset`: ScriptableObject、設定ファイル
- `.prefab`: プレハブ
- `.unity`: シーンファイル

### Phase 3: エージェント追加

```
agents/
├── unity-guide.md          # 統合ガイドエージェント（ドキュメント・ソース・パッケージ）
└── version-checker.md      # Unityバージョン情報
```

#### unity-guide エージェント
Unity 開発に関するドキュメント・ソースコード・パッケージ情報を統合的に提供。

参考:
- claude-code-system-prompts の claude-code-guide agent（プロンプト構造）
- nowsprinting/claude-code-settings-for-unity の rules/11-unity-documentation.md

```markdown
# Unity Guide Agent

Unity 開発に関する公式ドキュメント、ソースコード、パッケージ情報を
統合的に提供するエージェント。

## ドメイン

1. **Unity Engine/Editor API**: MonoBehaviour、GameObject、Component 等のコア API
2. **Unity ソースコード**: UnityCsReference による実装詳細
3. **UPM パッケージ**: Unity 公式パッケージ（uGUI、TextMeshPro、InputSystem 等）
4. **Unity YAML**: .meta、.asset、.prefab、.unity ファイルの形式
5. **NuGet パッケージ**: 外部 .NET ライブラリ

## 情報ソース

### Unity 公式ドキュメント
- **Manual** (docs.unity3d.com/{version}/Documentation/Manual/):
  - 概念説明、ワークフロー、ベストプラクティス
  - YAML: AssetMetadata, FormatDescription, UnityYAML, YAMLFileFormat, ClassIDReference

- **ScriptReference** (docs.unity3d.com/{version}/Documentation/ScriptReference/):
  - API リファレンス、クラス、メソッド、プロパティ

- **Package Documentation** (docs.unity3d.com/Packages/{package}@latest):
  - uGUI、TextMeshPro、InputSystem 等

### Unity ソースコード (UnityCsReference)
- **Base URL**: https://raw.githubusercontent.com/Unity-Technologies/UnityCsReference/master/
- **よく参照するパス**:
  - Runtime/Export/Scripting/{ClassName}.cs (MonoBehaviour, Component)
  - Runtime/Export/Director/{Name}.bindings.cs (PlayableGraph)
  - Editor/Mono/Inspector/{Name}Inspector.cs (カスタムインスペクタ)
  - Editor/Mono/GUI/{Name}.cs (エディタ GUI)
  - Modules/UI/Core/{Component}.cs (uGUI)
  - Modules/UIElements/{Name}.cs (UI Toolkit)
- **GitHub Search API**: クラス名からファイルパス特定
  https://api.github.com/search/code?q={ClassName}+repo:Unity-Technologies/UnityCsReference+extension:cs

### パッケージ情報
- **ローカル UPM** (./Library/PackageCache/{package}@{version}/):
  README.md, package.json (documentationUrl), CHANGELOG.md
- **Unity Registry**: packages.unity.com
- **OpenUPM**: openupm.com/packages/
- **NuGet**: nuget.org/packages/, ./Assets/packages.config

## アプローチ

1. unity-cli 機能でプロジェクトの Unity バージョンを取得
2. ユーザーの質問がどのドメインに該当するか判定
3. 適切な情報ソースを選択:
   - API の使い方 → 公式ドキュメント
   - 内部動作・実装詳細 → UnityCsReference
   - パッケージ導入・依存関係 → パッケージ情報
4. WebFetch で情報を取得
5. 公式情報に基づいてガイダンスを提供
6. 情報が不足する場合は WebSearch を使用
7. 必要に応じてローカルファイル (Read, Glob, Grep) を参照

## ガイドライン

- 公式ドキュメントを優先（推測より事実）
- ソースコードは「ドキュメントにない詳細」の補完として使用
- 簡潔でアクション指向の回答
- 具体例・コードスニペットを含める
- 参照元 URL を明示
- 関連機能をプロアクティブに提案
```

#### version-checker エージェント
Unity バージョン情報と機能対応表を取得。

**注意**: プロジェクトの Unity バージョン取得は既存の unity-cli 機能を使用。
このエージェントは外部情報（LTS、リリースノート等）の取得に特化。

```markdown
## 役割分担
- プロジェクトバージョン: unity-cli 既存機能 (ProjectVersion.txt)
- 外部バージョン情報: このエージェント

## 取得戦略
1. Unity リリースノート: unity.com/releases/editor/archive
2. LTS バージョン一覧
3. 機能別対応バージョン（特定機能がどのバージョンから使えるか）

## 出力形式
- 現在の LTS バージョン
- 最新 Tech Stream バージョン
- 特定機能の対応バージョン
- プロジェクトバージョンとの比較（アップグレード推奨等）
```


## 実装ステップ

### Step 0: Hook 層追加

#### Claude Code の hooks 機能

Claude Code は `hooks.json` でユーザー入力をインターセプトできる:

```
ユーザー入力
    ↓
hooks.json の matcher (正規表現) でマッチング
    ↓
マッチ → command (シェルスクリプト) を実行
    ↓
スクリプトの stdout が Claude のコンテキストに注入
    ↓
Claude が注入された指令に従って動作
```

#### 実装ファイル

```
.claude/plugins/unity-cli/
├── hooks/
│   └── hooks.json                    # キーワードマッチング設定
├── .claude/hooks/
│   └── unity-skill-eval-hook.sh      # 指令出力スクリプト
└── plugin.json                       # hooks パス参照
```

#### hooks.json の例

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "(?i)(Unity|MonoBehaviour|GameObject|\.cs\b|CS\\d{4}|コンパイル|テスト|ビルド|シーン|エラー)",
        "globs": ["**/ProjectSettings/ProjectVersion.txt"],
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/.claude/hooks/unity-skill-eval-hook.sh"
          }
        ]
      }
    ]
  }
}
```

**二重チェック**:
1. `globs`: Unity プロジェクト（ProjectVersion.txt 存在）でのみ Hook 発動
2. `matcher`: Unity 関連キーワードにマッチした場合のみ

#### unity-skill-eval-hook.sh の例

```bash
#!/bin/bash

# 二重チェック: Unity プロジェクトかどうか（globs のフォールバック）
if [ ! -f "ProjectSettings/ProjectVersion.txt" ]; then
  exit 0  # 何も出力せず終了
fi

cat << 'EOF'
=== UNITY-CLI SKILL ROUTING ===

このプロジェクトでは unity-cli が利用可能です。
質問タイプに応じて適切なスキルを使用してください:

| キーワード | スキル | 用途 |
|-----------|--------|------|
| コンパイル, テスト, 検証 | preflight | Refresh→Compile→Test |
| エラー, バグ, 調査 | debug | ErrorCapture→Analysis |
| ビルド | build | Build実行 |
| シーン, GameObject | scene | シーン構築 |
| アセット, 依存関係 | asset | アセット管理 |
| パフォーマンス, 最適化 | perf | Profiler実行 |
| UI, VisualElement | ui | UI Toolkit検査 |

API詳細が必要な場合は unity-guide エージェントを使用。
EOF
```

#### タスク

- [ ] `hooks/hooks.json` 作成 (100+ パターン)
- [ ] `.claude/hooks/unity-skill-eval-hook.sh` 作成
- [ ] plugin.json に hooks パス追加
- [ ] キーワードマッチャーテスト作成

### Step 1: unity-router スキル作成
- [ ] `skills/unity-router/SKILL.md` 作成
- [ ] ルーティングテーブル定義
- [ ] `rules/unity-router.md` にルーター優先ルール追加（プラグイン内、自動読み込み）

### Step 2: 既存スキルの強化
- [ ] ui に uGUI 対応を追加（または分割検討）
- [ ] scene, asset に YAML フォールバックを追加
- [ ] 各スキルに unity-guide エージェント連携を追加

### Step 3: unity-csharp の削除
- [ ] unity-csharp スキルを削除

### Step 4: エージェント追加
- [ ] unity-guide エージェント (統合: ドキュメント・ソース・パッケージ)
- [ ] version-checker エージェント (バージョン情報)

## 対象ファイル

```
/Users/bigdra/dev/github.com/bigdra50/unity-cli/
└── .claude/plugins/unity-cli/
    ├── hooks/
    │   └── hooks.json           # キーワードマッチング設定
    ├── .claude/hooks/
    │   └── unity-skill-eval-hook.sh  # 指令出力スクリプト
    ├── skills/
    │   └── unity-router/        # ルータースキル
    ├── agents/
    │   ├── unity-guide.md       # 統合ガイドエージェント
    │   └── version-checker.md   # バージョン情報
    ├── rules/
    │   └── unity-router.md      # ルーター優先ルール（自動読み込み）
    └── plugin.json              # hooks パス参照
```

**注意**: ユーザーの CLAUDE.md は変更しない。プラグイン内の rules/ は自動で読み込まれる。

## 参考: nowsprinting/claude-code-settings-for-unity

**方針**: rules は取り込まない（ユーザーが構築するもの）。agents の参照パターンのみ活用。

### エージェントに反映済み
- `11-unity-documentation.md`: ドキュメント参照パターン
  - プロジェクトの Unity バージョン検出
  - UPM パッケージのローカル参照
  - NuGet パッケージ参照

### ユーザー向け参考例として紹介
nowsprinting/claude-code-settings-for-unity は、Unity プロジェクト用の rules 構築の参考例として
ドキュメントで紹介する:

| ファイル | 用途 |
|----------|------|
| `00-code-of-conduct.md` | AI エージェントの行動規範 |
| `01-coding.md` | C# コーディング標準 |
| `02-testing.md` | テストガイドライン |
| `10-unity-project.md` | プロジェクト構造 |
| `12-unity-yaml.md` | YAML 編集ガイド |

## 検証方法

### ワークフローテスト（ユーザーの使い方に沿った検証）

1. **実装 → 検証サイクル**
   - C# ファイル編集 → Hook が preflight をトリガー
   - preflight: Refresh → Compile → EditModeTest → 結果確認

2. **エラー調査サイクル**
   - エラー報告 → Hook が debug をトリガー
   - debug: ErrorCapture → Classification → ContextGathering → 分析

3. **シーン構築サイクル**
   - シーン構築依頼 → Hook が scene をトリガー
   - scene: Survey → Create → Configure → Save

### Hook・Router 検証

0. Hook がキーワード検出で unity-router をトリガーするか確認
1. unity-router が質問タイプに応じて正しいスキルに振り分けるか

### エージェント検証

- unity-guide:
  - API ドキュメント: `Transform` などの ScriptReference 取得
  - ソースコード: UnityCsReference から実装詳細参照
  - パッケージ: `com.unity.textmeshpro` の情報取得
- version-checker: Unity LTS バージョン情報取得、既存機能との連携確認
