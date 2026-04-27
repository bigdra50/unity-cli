---
name: unity-build
description: |
  ビルドワークフロー。検証 → 設定確認 → ビルド実行 → エラー対応。
  Use for: "ビルド", "ビルド実行", "プラットフォーム設定", "ビルドエラー"
license: MIT
compatibility: Requires `u` CLI (unity-cli) and active Unity Editor via Relay Server.
metadata:
  openclaw:
    category: "game-development"
    user-invocable: true
    requires:
      bins: ["u"]
---

# unity-build

> **PREREQUISITE:** `../unity-shared/SKILL.md`

## ワークフロー

```text
1. /unity-verify Quick Verify   コンパイルエラーがないことを確認
2. ビルド設定確認              u build settings --json
3. ビルドシーン確認            u build scenes --json
4. ビルド実行                  u build run --target <platform> --output <path>
5. 結果確認                    成功/失敗を報告
```

## コマンド

```bash
u build settings --json                                      # 現在の設定
u build scenes --json                                        # ビルドシーン一覧
u build run --target StandaloneWindows64 --output ./Build     # ビルド実行
```

## プラットフォーム

| target | 値 |
|--------|---|
| Windows | `StandaloneWindows64` |
| macOS | `StandaloneOSX` |
| Android | `Android` |
| iOS | `iOS` |
| WebGL | `WebGL` |

## エラー対応

| エラー | 対応 |
|--------|------|
| コンパイルエラー | /unity-verify で修正ループ |
| Missing Scene | `u build scenes` で確認、シーンパス修正 |
| プラットフォーム未対応 | `u api call UnityEditor.EditorApplication ExecuteMenuItem --params '["File/Build Settings"]'` |
