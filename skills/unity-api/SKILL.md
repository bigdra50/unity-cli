---
name: unity-api
description: "Unity API の探索と実行。u api schema で検索、u api call で任意の public static メソッドを呼ぶ。"
user-invocable: true
metadata:
  openclaw:
    category: "game-development"
    requires:
      bins: ["u"]
    cliHelp: "u api --help"
---

# unity-api

> **PREREQUISITE:** `../unity-shared/SKILL.md`

既存 `u` コマンドにない操作を Unity API から直接呼ぶ。

## メソッド検索

```bash
u api schema --type AssetDatabase          # 型名でフィルタ
u api schema --namespace UnityEditor       # 名前空間でフィルタ
u api schema --method Refresh              # メソッド名で検索
u api schema --offline --type PlayerSettings  # キャッシュから (Relay 不要)
```

## メソッド呼び出し

```bash
u api call UnityEngine.Application get_unityVersion
u api call UnityEditor.AssetDatabase Refresh
u api call UnityEditor.AssetDatabase ImportAsset --params '["Assets/Prefabs/Player.prefab", 0]'
u api call UnityEditor.EditorApplication ExecuteMenuItem --params '["Window/General/Console"]'
```

## よく使うパターン

| 用途 | コマンド |
|------|---------|
| プロジェクト設定 | `u api call UnityEditor.PlayerSettings get_productName` |
| コンパイル状態 | `u api call UnityEditor.EditorApplication get_isCompiling` |
| アセット存在確認 | `u api call UnityEditor.AssetDatabase AssetPathExists --params '["Assets/..."]'` |
| フォルダ作成 | `u api call UnityEditor.AssetDatabase CreateFolder --params '["Assets", "New"]'` |
| メニュー実行 | `u api call UnityEditor.EditorApplication ExecuteMenuItem --params '["Tools/..."]'` |

## 制約

- static メソッドのみ
- 引数: プリミティブ, string, enum, プリミティブ配列
- UnityEngine / UnityEditor 名前空間のみ
- [Obsolete] メソッドは除外済み

## 既存コマンドとの使い分け

既存コマンド (`u scene`, `u build` 等) がある操作はそちらを使う。`u api` は既存コマンドがカバーしない操作のためのフォールバック。
