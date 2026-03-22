---
name: unity-perf
description: |
  パフォーマンス計測ワークフロー。プロファイリング、GC 分析、最適化提案。
  Use for: "パフォーマンス", "プロファイル", "FPS", "GC", "最適化", "ボトルネック"
user-invocable: true
metadata:
  openclaw:
    category: "game-development"
    requires:
      bins: ["u"]
---

# unity-perf

> **PREREQUISITE:** `../unity-shared/SKILL.md`

## プロファイリングフロー

```
1. /unity-verify Quick Verify      コンパイルエラーがないことを確認
2. u play                          Play Mode 開始
3. u profiler start                プロファイリング開始
4. 計測 (数秒〜数十秒)
5. u profiler snapshot             スナップショット取得
   u profiler frames --count 10   フレームデータ取得
6. u profiler stop                 停止
7. u stop                          Play Mode 終了
8. 分析 → 最適化提案
```

## コマンド

```bash
u profiler start                  # 開始
u profiler stop                   # 停止
u profiler snapshot               # 現在のスナップショット
u profiler frames --count 10      # 直近Nフレーム
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
