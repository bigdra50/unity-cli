---
name: unity-asset
description: |
  アセット管理ワークフロー。依存関係調査、参照整合性チェック、パッケージ管理。
  Use for: "アセット依存", "参照切れ", "パッケージ管理", "不要アセット"
user-invocable: true
metadata:
  openclaw:
    category: "game-development"
    requires:
      bins: ["u"]
---

# unity-asset

> **PREREQUISITE:** `../unity-shared/SKILL.md`

## 調査フロー

```text
1. アセット情報   u asset info <path>
2. 依存関係      u asset deps <path>
3. 参照元        u asset refs <path>
4. 問題検出 → 修正 → /unity-verify
```

## コマンド

### アセット操作

```bash
u asset info "Assets/Prefabs/Player.prefab"    # 基本情報
u asset deps "Assets/Prefabs/Player.prefab"    # 依存先一覧
u asset refs "Assets/Prefabs/Player.prefab"    # 参照元一覧
u asset prefab "Assets/Prefabs/X.prefab" --target "X"  # Prefab 化
u asset scriptable-object "Assets/Data/Config.asset" --type "GameConfig"
```

### パッケージ管理

```bash
u package list                           # インストール済みパッケージ
u package add com.unity.inputsystem      # 追加
u package remove com.unity.inputsystem   # 削除
```

## CLI 非対応操作

unity-shared のフォールバック順に従う:
1. `u api schema --type AssetDatabase` で対応メソッドを検索 (107メソッド)
2. `u api call` で実行
3. .meta インポート設定は YAML 直接編集
