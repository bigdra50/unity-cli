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

## インスタンス指定 (必須)

unity-* スキル経由で `u` コマンドを呼ぶ際は **必ず `-i <instance>` を付ける**。default インスタンスに依存しない。

```bash
u -i <instance> refresh    # OK
u refresh                  # NG (skill 経由では使わない)
```

`<instance>` はユーザーから渡される or 親セッションが指定する値で置き換える。`u instances` で接続中 Unity 一覧を確認できる。本ドキュメント以下のサンプルでは `<instance>` をそのまま使うが、実行時は具体名 (例: `TestProject`) に置換する。

理由: 複数 Unity 接続環境で誤ったインスタンスへコマンドを送るリスクと、subagent 間の挙動を default 依存にしないため。

## 接続確認

```bash
u instances             # 接続中 Unity 一覧
u -i <instance> state   # 特定エディタの状態
```

接続不可時: `unity-relay --port 6500` で Relay 起動。

## Quick Verify

コード変更後に毎回実行する検証シーケンス。順序厳守 (clear は refresh の**前**に置く。後にすると refresh の診断ログを消してしまう)。

```bash
# 1. 既存ログをクリア (refresh の診断を残すため refresh の前)
u -i <instance> console clear

# 2. AssetDatabase リフレッシュ (コンパイルトリガー)
u -i <instance> refresh

# 3. isCompiling が false になるまでポーリング (2秒間隔, 最大30秒)
for _ in $(seq 1 15); do
  u -i <instance> state --json | jq -e '.isCompiling == false' >/dev/null && break
  sleep 2
done

# 4. Error/Warning 取得 (--count は deprecated. head -N を使う)
u -i <instance> console get -l E,W | head -50
```

`u state --json` の出力例 (抜粋, キーはトップレベル):

```json
{"isCompiling": false, "isPlaying": false, "isPaused": false}
```

- Error あり → 修正して再実行 (最大3回)
- Warning のみ → 報告して続行

### 注記: 空 (0 行) は「クリーン」だが「Warning が無い」とは限らない

Unity はインクリメンタルコンパイルのため、ソース未変更で `refresh` を呼んでも再コンパイルは走らず、過去の Warning は再出力されない。`console clear` 後に空が返っても以下のいずれかを意味する:

1. ソース変更があり再コンパイルが走り、エラー/警告がない (本当のクリーン)
2. ソース未変更で再コンパイルがスキップされ、過去の警告が出力されないだけ

**直前にソース編集があった文脈なら「クリーン」扱いで OK**。過去の警告を確実に確認したい場合は対象ファイルの touch (`touch Assets/.../Foo.cs`) で mtime を更新してから refresh するか、`Library/ScriptAssemblies/` をクリアする。

## フォールバック順

CLI 非対応の操作を行う場合:

```text
1. u -i <instance> <既存コマンド>           最優先
2. u -i <instance> api call Type Method    5,243 メソッド対応
3. YAML 直接編集                            最終手段 (.meta インポート設定等)
```

## セキュリティ

- `u api call` は UnityEngine / UnityEditor のみ許可
- 破壊的操作の実行前にユーザー確認
