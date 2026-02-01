#!/bin/bash
# Unity Skills Meta-Cognition Hook
# Unity 関連キーワードを検出した際に、適切なスキルへのルーティングを指示

# 二重チェック: Unity プロジェクトかどうか（globs のフォールバック）
if [ ! -f "ProjectSettings/ProjectVersion.txt" ]; then
  exit 0  # 何も出力せず終了
fi

cat << 'EOF'

=== UNITY-CLI SKILL ROUTING ===

このプロジェクトでは unity-cli が利用可能です。
質問タイプに応じて適切なスキルを使用してください。

## STEP 1: 質問タイプを識別

### Layer 2 シグナル（ワークフロー）

| キーワード | スキル | 用途 |
|-----------|--------|------|
| コンパイル, テスト, 検証, verify | /preflight | Refresh→Compile→EditModeTest |
| エラー, バグ, 調査, debug, 例外 | /debug | ErrorCapture→Classification→Analysis |
| ビルド, build, apk, aab | /build | Build実行 |
| シーン, scene, GameObject配置 | /scene | シーン構築（YAML フォールバック対応） |
| アセット, asset, 依存関係, prefab | /asset | アセット管理（YAML フォールバック対応） |
| パフォーマンス, 最適化, profiler | /perf | Profiler実行→分析 |
| UI, VisualElement, Canvas, uGUI | /ui | UI 検査（UI Toolkit + uGUI 対応） |

### Layer 1 シグナル（API 操作 - エラーコード）

| パターン | 対応 |
|---------|------|
| CS0029, CS0030, CS0266 | 型変換エラー → /debug |
| CS0103, CS0246, CS0234 | 名前解決エラー → /debug |
| NullReferenceException | Null参照 → /debug |
| MissingReferenceException | 破棄オブジェクト参照 → /debug |

## STEP 2: スキル読み込み

識別されたキーワードに基づき、Skill() ツールで適切なスキルを読み込む:

1. ワークフロー質問 → 対応する /uXXX スキル
2. API 詳細が必要 → unity-guide エージェント（Task ツール）
3. バージョン情報が必要 → version-checker エージェント（Task ツール）

## STEP 3: 出力形式

### 分析結果
- 質問タイプ: [ワークフロー / API 詳細 / エラー調査 / ...]
- 推奨スキル: [/uXXX]
- 理由: [なぜこのスキルが適切か]

### 補足情報が必要な場合
- API ドキュメント参照: unity-guide エージェント使用
- Unity バージョン確認: u project info または unity-guide エージェント

## unity-cli コマンド一覧

基本操作:
- u state / u play / u stop / u pause / u refresh
- u instances / u project info

シーン・オブジェクト:
- u scene active / u scene hierarchy / u scene load <path>
- u gameobject find/create/modify/delete

アセット:
- u asset info <path> / u asset deps <path> / u asset refs <path>
- u asset prefab <gameobject> <path>

テスト・ビルド:
- u tests run edit/play / u tests list edit/play
- u build settings / u build run

コンソール・プロファイラ:
- u console get -l E / u console clear
- u profiler status/start/stop/snapshot

UI:
- u uitree dump -p "GameView" / u uitree query -p "Panel" -t Button
- u uitree inspect ref_N

===================================

EOF
