---
name: uperf
description: |
  Unityパフォーマンス最適化ワークフロー。プロファイリング、GC分析、バッチング最適化、ボトルネック特定を行う。
  Use for: "パフォーマンス", "プロファイル", "FPS", "GC", "最適化", "ボトルネック"
user-invocable: true
---

# Unity Performance Profiling Workflow

プロファイリングによるボトルネック特定・分析・最適化提案を行うワークフロー。

## CLI Setup

```bash
# グローバルインストール済みの場合
u <command>

# uvx 経由（インストール不要）
uvx --from git+https://github.com/bigdra50/unity-cli u <command>
```

以下のワークフロー内では `u` コマンドを使用する。

## Decision Criteria

| 状況 | フロー |
|------|--------|
| FPSが低い・カクつく | Profiling Flow → CPU/GPU 分析 |
| GC Spike が発生する | Profiling Flow → GC 分析 → コードレビュー |
| ドローコールが多い | Profiling Flow → バッチング分析 |
| 特定シーンで重い | Profiling Flow → フレーム比較分析 |
| メモリ使用量が高い | Profiling Flow → メモリ分析 |
| 最適化方針を知りたい | Optimization Checklist 参照 |

## Profiling Flow

```
Request (パフォーマンス調査)
  │
  ▼
┌─────────────────────────────┐
│ Step 1: Play Mode 開始      │
│ u play                      │
│ u state (poll until         │
│   isPlaying == true)        │
└──────────┬──────────────────┘
           ▼
┌─────────────────────────────┐
│ Step 2: Profiler Start      │
│ u profiler start            │
│ u profiler status (確認)    │
└──────────┬──────────────────┘
           ▼
┌─────────────────────────────┐
│ Step 3: Data Collection     │
│ (操作・シーン遷移などを     │
│  実行して負荷をかける)      │
│ wait 5-10s                  │
└──────────┬──────────────────┘
           ▼
┌─────────────────────────────┐
│ Step 4: Snapshot / Frames   │
│ u profiler snapshot         │
│ u profiler frames -c 30     │
└──────────┬──────────────────┘
           ▼
┌─────────────────────────────┐
│ Step 5: Stop & Analyze      │
│ u profiler stop             │
│ u stop                      │
└──────────┬──────────────────┘
           ▼
      Analysis & Report
```

## Step Details

### Step 1: Play Mode 開始

```bash
u play
```

Play Mode に入ったことを確認:

```bash
u state
# isPlaying が true になるまでポーリング（最大10秒）
```

### Step 2: Profiler Start

```bash
u profiler start
```

プロファイラが動作中か確認:

```bash
u profiler status
```

### Step 3: Data Collection

負荷が発生する状況を再現する。ユーザーに操作を依頼するか、スクリプトで負荷シーンに遷移する。

待機時間の目安:
- 定常状態の計測: 5秒
- 負荷ピークの計測: 10秒
- GC 発生パターン確認: 10-15秒

### Step 4: Data Acquisition

現フレームのスナップショット:

```bash
u profiler snapshot
```

直近Nフレームの時系列データ:

```bash
u profiler frames -c 30
```

### Step 5: Stop

```bash
u profiler stop
u stop
```

## Analysis Patterns

取得データから以下のパターンでボトルネックを判定する。

### CPU ボトルネック

判定条件: `cpuFrameTimeMs` が目標フレーム時間を超過

| ターゲットFPS | フレーム予算 |
|---------------|-------------|
| 60 FPS | 16.6ms |
| 30 FPS | 33.3ms |

対処:
1. snapshot で cpuFrameTimeMs を確認
2. 高コスト処理を特定（Physics, Animation, Scripts 等）
3. 該当コードのレビュー → 最適化

### GPU ボトルネック

判定条件: `gpuFrameTimeMs` が目標フレーム時間を超過

対処:
1. snapshot で gpuFrameTimeMs を確認
2. batches / drawCalls を確認
3. シェーダー複雑度・オーバードローを疑う

### GC 問題

判定条件: `gcAllocBytes` が高い、または GC Spike がフレームデータに出現

対処:
1. frames データで gcAllocBytes の推移を確認
2. 毎フレーム GC Alloc が発生しているか確認
3. 原因コードを特定してレビュー

GC Alloc を引き起こす典型パターン:
- `string` 結合（`+` 演算子）
- LINQ の `ToList()`, `ToArray()`
- `foreach` on non-generic collections
- `GetComponent<T>()` の毎フレーム呼び出し
- `new` によるヒープ割り当て（Update 内）
- ボクシング（値型 → object 変換）

### バッチング問題

判定条件: `batches` / `drawCalls` が想定より多い

対処:
1. snapshot で batches, drawCalls を確認
2. 原因を分類:
   - マテリアルが多すぎる → アトラス化、マテリアル共有
   - Dynamic Batching が効いていない → 頂点数制限を確認
   - SRP Batcher 非対応シェーダー → シェーダー修正

## Optimization Checklist

### CPU 最適化

- [ ] Update() 内の処理を最小限にする
- [ ] 重い処理はコルーチンや Job System で分散
- [ ] Physics のFixed Timestep を調整
- [ ] OnGUI / OnDrawGizmos が残っていないか確認
- [ ] string 操作を StringBuilder に置き換え
- [ ] GetComponent のキャッシュ化

### GPU 最適化

- [ ] Draw Call 数を確認（目標: モバイル100以下、PC 1000以下）
- [ ] Static/Dynamic Batching の有効化
- [ ] LOD の設定
- [ ] オーバードローの削減（半透明オブジェクト整理）
- [ ] シェーダーバリアント数の削減

### メモリ最適化

- [ ] テクスチャの MaxSize / Compression 設定
- [ ] 不要なアセット参照の解除
- [ ] Resources フォルダの使用を最小限に
- [ ] Addressables によるオンデマンドロード
- [ ] Audio の LoadType 設定（Streaming for BGM）

### GC 最適化

- [ ] Update 内の GC Alloc を0にする
- [ ] オブジェクトプーリングの導入
- [ ] string 結合を StringBuilder に
- [ ] LINQ を for/foreach ループに置き換え
- [ ] コレクションの事前確保（capacity 指定）

## Anti-Patterns

| NG | 理由 | 対策 |
|----|------|------|
| Play Mode 外でプロファイリング | ランタイムの実際の負荷が計測できない | 必ず Play Mode で計測 |
| 1フレームだけで判断 | フレームごとのばらつきを見逃す | frames -c 30 で時系列を確認 |
| Editor 上の数値をそのまま信用 | Editor オーバーヘッドが含まれる | 実機ビルドでの計測が正確と補足する |
| 最適化前にプロファイルしない | 効果の薄い箇所に時間を費やす | 計測 → 特定 → 最適化の順を守る |
| frames を大量取得 | トークンを大量消費 | -c 30 程度に絞る |
| 全項目を一度に最適化 | 効果の切り分けができない | 1項目ずつ変更・計測を繰り返す |

## Token-Saving Strategies

| 状況 | 対応 |
|------|------|
| フレームデータが長い | `-c 30` で30フレームに絞る |
| snapshot で十分 | frames を取得せず snapshot のみ使用 |
| Warning が大量 | `-l +W` は避け、必要な場合のみ取得 |
| 繰り返し計測 | 前回データとの差分のみ報告 |

## Result Report Format

```
## Performance Profile Report

- Target FPS: 60
- Measured Frames: 30
- CPU Frame Time: avg Xms / max Xms
- GPU Frame Time: avg Xms / max Xms
- Draw Calls: X
- Batches: X
- GC Alloc: X KB/frame
- Bottleneck: CPU / GPU / GC / Batching / None
- Recommendations:
  - (具体的な改善項目)
```

## Related Skills

| スキル | 関係 |
|--------|------|
| uverify | 最適化コード変更後のビルド検証・テスト実行 |
| unity-csharp | GC最適化やパフォーマンス改善のコーディングパターン |
