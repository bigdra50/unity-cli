---
name: unity-verify
description: |
  コード変更後の検証ワークフロー。refresh → コンパイル待ち → エラー確認 → 任意でテスト。
  Use for: "検証して", "コンパイル確認", "テスト実行", "verify", "preflight"
license: MIT
compatibility: Requires `u` CLI (unity-cli) and active Unity Editor via Relay Server.
metadata:
  openclaw:
    category: "game-development"
    user-invocable: true
    requires:
      bins: ["u"]
---

# unity-verify

> **PREREQUISITE:** `../unity-shared/SKILL.md`

## Quick Verify

コード変更するたびに実行。unity-shared の Quick Verify そのもの。

```text
u refresh → isCompiling ポーリング → u console clear → u console get -l E,W
→ Error あり: 修正して再実行 (最大3回)
→ クリーン: 完了
```

## Full Verify

ユーザーが要求した場合のみ。Quick Verify + EditMode テスト。

```text
Quick Verify 実行
→ クリーンなら u tests run edit → 結果確認
→ Fail あり: 報告、修正して Quick Verify から再実行
```

## Runtime Check

要求された場合のみ。Play Mode でランタイムエラーを検出。

```text
u console clear → u play → isPlaying ポーリング → 3秒待機 → u console get -l +E+X → u stop
```

報告のみ。自動修正せずユーザーに判断を委ねる。

## Auto-trigger

以下の編集後に Quick Verify を自動実行:
- `.cs` / `.shader` / `.compute`
- `.asmdef` / `.asmref`
- Unity パッケージ関連 (`package.json` / `manifest.json`)

スキップ: コメントのみの変更、プロジェクト外ファイル、ユーザー指示。
