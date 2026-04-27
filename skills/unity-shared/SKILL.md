---
name: unity-shared
description: "unity-cli 共通ルール。全 unity-* スキルが自動ロードする前提条件。Use as prerequisite for any unity-* skill (verification sequence, fallback order, security policy)."
license: MIT
compatibility: Requires `u` CLI (unity-cli) and active Unity Editor via Relay Server.
metadata:
  openclaw:
    category: "game-development"
    user-invocable: false
    requires:
      bins: ["u"]
    cliHelp: "u --help"
---

# unity-shared

全 unity-* スキルが従う共通ルール。

## 接続

```bash
u instances    # 接続中 Unity 一覧
u state        # エディタ状態
```

接続不可時: `unity-relay --port 6500` で Relay 起動。

## Quick Verify

コード変更後に毎回実行する検証シーケンス。

```bash
u refresh                          # AssetDatabase リフレッシュ
# u state --json ポーリング (isCompiling == false まで、2秒間隔、最大30秒)
u console clear                    # ログクリア
u console get -l E,W --count 50    # Error/Warning 取得
```

- Error あり → 修正して再実行 (最大3回)
- Warning のみ → 報告して続行

## フォールバック順

CLI 非対応の操作を行う場合:

```text
1. u <既存コマンド>           最優先
2. u api call Type Method    5,243 メソッド対応
3. YAML 直接編集              最終手段 (.meta インポート設定等)
```

## セキュリティ

- `u api call` は UnityEngine / UnityEditor のみ許可
- 破壊的操作の実行前にユーザー確認
