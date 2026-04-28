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

> **PREREQUISITE:** `../unity-shared/SKILL.md`（Relay Server 経由で Unity Editor が起動/アクティブであること）
>
> skill 経由のコマンドは必ず `-i <instance>` を付ける (unity-shared #インスタンス指定)。

## 調査フロー

```text
1. エラー取得      u -i <instance> console get -l E,X | head -20
2. エラー分類      → コンパイルエラー / ランタイムエラー / Missing 系
3. コンテキスト収集  u -i <instance> scene hierarchy / u -i <instance> component inspect / u -i <instance> screenshot
4. 原因特定 → 修正 → /unity-verify で検証
```

## エラー分類と対応

| エラー種別 | 対応 |
|-----------|------|
| CS0XXX (コンパイルエラー) | コード修正 → /unity-verify |
| NullReferenceException | `u -i <instance> scene hierarchy` + `u -i <instance> component inspect` で参照確認 |
| MissingReferenceException | `u -i <instance> asset info` でアセット存在確認 |
| MissingComponentException | `u -i <instance> component list` で確認 → `u -i <instance> component add` |

## コンソール操作

```bash
u -i <instance> console get                   # 全ログ
u -i <instance> console get -l E | head -10   # Error のみ、先頭10件
u -i <instance> console get -l E,W            # Error + Warning
u -i <instance> console clear                 # ログクリア
```

## 状態確認

```bash
u -i <instance> screenshot          # エディタのスクリーンショット
u -i <instance> scene hierarchy     # 現在のシーン構造
u -i <instance> state               # Play/Pause/Compile 状態
```

コンパイルエラーが解決しない場合は /unity-verify に切り替える。
