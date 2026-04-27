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

> **PREREQUISITE:** `../unity-shared/SKILL.md`

## ワークフロー

```text
1. 現状把握     u scene active / u scene hierarchy
2. オブジェクト  u gameobject create / find / modify / delete
3. コンポーネント u component add / modify / inspect / list
4. Prefab化     u asset prefab <path> --target <name>
5. シーン保存   u scene save
```

## コマンドリファレンス

### Scene

```bash
u scene active                    # アクティブシーン情報
u scene hierarchy --depth 2       # 階層表示
u scene load --path "Assets/..."  # シーン読み込み
u scene save                      # 保存
```

### GameObject

```bash
u gameobject create "Player"                          # 空オブジェクト
u gameobject create "Cube" --primitive Cube            # プリミティブ
u gameobject find --name "Player"                      # 検索
u gameobject modify -n "Player" --position 0,1,0       # Transform変更
u gameobject delete -n "Player"                        # 削除
```

### Component

```bash
u component list -t "Player"                                      # 一覧
u component inspect -t "Player" -T Rigidbody                      # 詳細
u component add -t "Player" -T Rigidbody                          # 追加
u component modify -t "Player" -T Rigidbody --prop mass --value 2 # 変更
u component remove -t "Player" -T Rigidbody                       # 削除
```

### Asset

```bash
u asset prefab "Assets/Prefabs/Player.prefab" --target "Player"  # Prefab化
u asset info "Assets/Prefabs/Player.prefab"                       # 情報
```

## CLI 非対応操作

unity-shared のフォールバック順に従う:
1. `u api schema --type <Type>` で対応メソッドを検索
2. `u api call` で実行
3. .meta インポート設定等は YAML 直接編集
