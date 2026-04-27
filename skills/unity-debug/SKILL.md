---
name: unity-debug
description: |
  ランタイムエラー・NullReference・コンソールログの調査ワークフロー。
  Use for: "エラー調査", "NullReference", "デバッグ", "コンソール確認", "ログ確認"
license: MIT
compatibility: Requires `u` CLI (unity-cli) and active Unity Editor via Relay Server.
metadata:
  openclaw:
    category: "game-development"
    user-invocable: true
    requires:
      bins: ["u"]
---

# unity-debug

> **PREREQUISITE:** `../unity-shared/SKILL.md`

## 調査フロー

```text
1. エラー取得      u console get -l E,X --count 20
2. エラー分類      → コンパイルエラー / ランタイムエラー / Missing 系
3. コンテキスト収集  u scene hierarchy / u component inspect / u screenshot
4. 原因特定 → 修正 → /unity-verify で検証
```

## エラー分類と対応

| エラー種別 | 対応 |
|-----------|------|
| CS0XXX (コンパイルエラー) | コード修正 → /unity-verify |
| NullReferenceException | `u scene hierarchy` + `u component inspect` で参照確認 |
| MissingReferenceException | `u asset info` でアセット存在確認 |
| MissingComponentException | `u component list` で確認 → `u component add` |

## コンソール操作

```bash
u console get                      # 全ログ
u console get -l E --count 10      # Error のみ、先頭10件
u console get -l E,W               # Error + Warning
u console clear                    # ログクリア
```

## 状態確認

```bash
u screenshot                       # エディタのスクリーンショット
u scene hierarchy                  # 現在のシーン構造
u state                            # Play/Pause/Compile 状態
```

コンパイルエラーが解決しない場合は /unity-verify に切り替える。
