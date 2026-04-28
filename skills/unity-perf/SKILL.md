---
name: unity-perf
description: |
  パフォーマンス計測ワークフロー。プロファイリング、GC 分析、最適化提案。
  Use for: "パフォーマンス", "プロファイル", "FPS", "GC", "最適化", "ボトルネック"
license: MIT
compatibility: Requires `u` CLI (unity-cli) and active Unity Editor via Relay Server.
metadata:
  openclaw:
    category: "game-development"
    user-invocable: true
    requires:
      bins: ["u"]
---

# unity-perf

> **PREREQUISITE:** `../unity-shared/SKILL.md`（Relay Server 経由で Unity Editor が起動/アクティブであること）
>
> skill 経由のコマンドは必ず `-i <instance>` を付ける (unity-shared #インスタンス指定)。

## プロファイリングフロー

```text
1. /unity-verify Quick Verify             コンパイルエラーがないことを確認
2. u -i <instance> play                   Play Mode 開始
3. u -i <instance> profiler start         プロファイリング開始
4. 計測 (数秒〜数十秒)
5. u -i <instance> profiler snapshot      スナップショット取得
   u -i <instance> profiler frames --count 10   フレームデータ取得
6. u -i <instance> profiler stop          停止
7. u -i <instance> stop                   Play Mode 終了
8. 分析 → 最適化提案
```

## コマンド

```bash
u -i <instance> profiler start                  # 開始
u -i <instance> profiler stop                   # 停止
u -i <instance> profiler snapshot               # 現在のスナップショット
u -i <instance> profiler frames --count 10      # 直近Nフレーム
```

## 分析パターン

| ボトルネック | 確認方法 | 対策 |
|-------------|---------|------|
| CPU | frames の処理時間 | ホットパスの最適化 |
| GPU | frames の描画時間 | バッチング、LOD |
| GC | frames の GC Alloc | オブジェクトプール、struct 化 |
| メモリ | snapshot のメモリ使用量 | アセット圧縮、参照整理 |

## 最適化チェックリスト

- [ ] Update/LateUpdate 内の毎フレーム Alloc
- [ ] GetComponent の繰り返し呼び出し
- [ ] 文字列結合 (+ 演算子)
- [ ] LINQ in Update
- [ ] 不要な SetActive 切り替え
