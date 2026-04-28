---
name: unity-scene
description: |
  シーン構築ワークフロー。オブジェクト配置、コンポーネント設定、Prefab化、シーン保存。
  Use for: "シーン構築", "オブジェクト配置", "Prefab化", "コンポーネント設定"
license: MIT
compatibility: Requires `u` CLI (unity-cli) and active Unity Editor via Relay Server.
metadata:
  openclaw:
    category: "game-development"
    user-invocable: true
    requires:
      bins: ["u"]
---

# unity-scene

> **PREREQUISITE:** `../unity-shared/SKILL.md`（Relay Server 経由で Unity Editor が起動/アクティブであること）
>
> skill 経由のコマンドは必ず `-i <instance>` を付ける (unity-shared #インスタンス指定)。

## ワークフロー

```text
1. 現状把握     u -i <instance> scene active / u -i <instance> scene hierarchy
2. オブジェクト  u -i <instance> gameobject create / find / modify / delete
3. コンポーネント u -i <instance> component add / modify / inspect / list
4. Prefab化     u -i <instance> asset prefab <path> --target <name>
5. シーン保存   u -i <instance> scene save
```

## コマンドリファレンス

### Scene

```bash
u -i <instance> scene active                    # アクティブシーン情報
u -i <instance> scene hierarchy --depth 2       # 階層表示
u -i <instance> scene load --path "Assets/..."  # シーン読み込み
u -i <instance> scene save                      # 保存
```

### GameObject

```bash
u -i <instance> gameobject create "Player"                          # 空オブジェクト
u -i <instance> gameobject create "Cube" --primitive Cube           # プリミティブ
u -i <instance> gameobject find --name "Player"                     # 検索
u -i <instance> gameobject modify -n "Player" --position 0,1,0      # Transform変更
u -i <instance> gameobject delete -n "Player"                       # 削除
```

### Component

```bash
u -i <instance> component list -t "Player"                                      # 一覧
u -i <instance> component inspect -t "Player" -T Rigidbody                      # 詳細
u -i <instance> component add -t "Player" -T Rigidbody                          # 追加
u -i <instance> component modify -t "Player" -T Rigidbody --prop mass --value 2 # 変更
u -i <instance> component remove -t "Player" -T Rigidbody                       # 削除
```

### Asset

```bash
u -i <instance> asset prefab "Assets/Prefabs/Player.prefab" --target "Player"  # Prefab化
u -i <instance> asset info "Assets/Prefabs/Player.prefab"                       # 情報
```

## CLI 非対応操作

unity-shared のフォールバック順に従う:
1. `u -i <instance> api schema --type <Type>` で対応メソッドを検索
2. `u -i <instance> api call` で実行
3. .meta インポート設定等は YAML 直接編集
