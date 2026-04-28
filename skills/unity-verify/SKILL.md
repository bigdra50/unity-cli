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

> **PREREQUISITE:** `../unity-shared/SKILL.md`（Relay Server 経由で Unity Editor が起動/アクティブであること）

## Quick Verify

コード変更するたびに実行。unity-shared の Quick Verify (#quick-verify) を参照。skill 経由のコマンドは必ず `-i <instance>` を付ける (unity-shared #インスタンス指定)。

```text
u -i <instance> console clear
→ u -i <instance> refresh
→ isCompiling ポーリング (2s 間隔, 最大 30s)
→ u -i <instance> console get -l E,W | head -50
```

### 結果判定

`u console get` の出力に対して以下のテーブルで判定。出力ゼロ行 = エラー無しとして扱う (空 = OK)。

| 出力内容 | 判定 | 次のアクション |
|----------|------|---------------|
| 空 (0 行) | **クリーン** | 完了。次工程 (Full Verify 等) に進める |
| `[ERROR]` 行のみ無し ＋ `[WARN]` 行あり | **クリーン (Warning 許容)** | Warning を 1〜3 行に要約してユーザー報告、続行 |
| `[ERROR]` 行あり | **エラー** | 下記「修正ループ」へ |

`-l E,W` は Error + Warning 両方を取得する。Warning だけなら続行可、Error が 1 件でもあれば停止して修正ループに入る。

### 修正ループ (Error 検出時)

最大 3 回までの「修正 → Quick Verify 再実行」サイクル。

1. **修正前にユーザー確認 (default)**: 以下のいずれかに該当する場合は自動修正せずユーザーに修正方針を確認する
   - ファイル名 prefix が `_` (例: `_Broken*.cs`) または "Test" "Fixture" 等を含む
   - エラーファイル内コメントに `intentional`, `TODO`, `FIXME`, `tuning` 等の意図的破壊を示唆する語がある
   - 1 回の修正で 3 ファイル以上に変更が及ぶ場合
   - 既存ロジックの大幅変更が必要な場合 (型変更、API 置換、import 追加以外の構造変更)
2. **自動修正可**: 単純なタイプミス (セミコロン抜け、スペル間違い、import 不足) で 1 ファイル限定の場合は試行 OK
3. **ループ運用**: 修正 → Quick Verify を最大 3 回繰り返す。3 回で解消しない場合はユーザーに状況を報告し判断を仰ぐ
4. **副作用回避**: 1 回の修正は 1 ファイル単位。無関係な変更 (フォーマット整形、リファクタ) を混ぜない

## Full Verify

ユーザーが要求した場合のみ。Quick Verify + EditMode テスト。

```text
Quick Verify 実行
→ クリーン (Error 0、Warning は許容) なら u tests run edit → 結果確認
→ Fail あり: 報告、修正して Quick Verify から再実行 (修正ループの規定に従う)
```

## Runtime Check

要求された場合のみ。Play Mode でランタイムエラーを検出。

```text
u -i <instance> console clear
→ u -i <instance> play
→ isPlaying ポーリング
→ 3秒待機
→ u -i <instance> console get -l +E+X
→ u -i <instance> stop
```

報告のみ。自動修正せずユーザーに判断を委ねる。

## Auto-trigger

以下の編集後に Quick Verify を自動実行:
- `.cs` / `.shader` / `.compute`
- `.asmdef` / `.asmref`
- Unity パッケージ関連 (`package.json` / `manifest.json`)

スキップ: コメントのみの変更、プロジェクト外ファイル、ユーザー指示。
