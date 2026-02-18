---
name: unity-ui
description: |
  UI 開発ドメインスキル。UI Toolkit と uGUI の両方に対応。ビジュアルツリー検査と開発イテレーション（作成→Play確認→修正ループ）を提供する。
  Use for: "UI確認", "UIツリー", "UI Toolkit検査", "UI作って", "UI修正して", "UIレイアウト", "VisualElement調べて", "Canvas", "uGUI", "Image", "Text", "Button"
user-invocable: true
---

# Unity UI Development

UI Toolkit および uGUI によるUI開発を支援する。ツリー検査と開発イテレーションの2つのフローを提供。

## UI システム判定

| 特徴 | UI Toolkit | uGUI |
|------|-----------|------|
| ルート要素 | UIDocument | Canvas |
| スタイル | USS | RectTransform + 各コンポーネント |
| 要素 | VisualElement | Image, Text, Button 等 |
| 検査コマンド | u uitree | u component inspect |
| 推奨用途 | エディタ拡張、新規UI | 既存プロジェクト、レガシーUI |

質問内容から UI システムを判定:
- `VisualElement`, `UXML`, `USS`, `UIDocument` → UI Toolkit
- `Canvas`, `Image`, `Text`, `Button`, `RectTransform` → uGUI

## CLI Setup

```bash
u <command>
```

## Decision Criteria

| 状況 | 使うフロー |
|------|-----------|
| UIが表示されない/崩れている | Inspection Flow |
| 新しいUIを作りたい | Development Iteration Flow |
| 既存UIのスタイルを調整したい | Development Iteration Flow |
| 特定要素のプロパティを確認したい | Inspection Flow → inspect |

## Inspection Flow

UI構造やスタイルの問題を調査する。

```
UI Issue / Layout Question
  │
  ▼
┌─────────────────────────────┐
│ Step 1: Panel Discovery     │
│ u uitree dump               │
└──────────┬──────────────────┘
           ▼
┌─────────────────────────────┐
│ Step 2: Tree Overview       │
│ u uitree dump -p <panel>    │
└──────────┬──────────────────┘
           ▼
┌─────────────────────────────┐
│ Step 3: Element Query       │
│ u uitree query -p <panel>   │
│   -t/-n/-c (絞り込み)       │
└──────────┬──────────────────┘
           ▼
┌─────────────────────────────┐
│ Step 4: Detail Inspection   │
│ u uitree inspect <ref_id>   │
│   --style --children        │
└──────────┬──────────────────┘
           ▼
      Analyze & Report
```

### Panel Discovery

```bash
u uitree dump                 # パネル一覧
```

ランタイム UI は通常 `GameView`。エディタ拡張は `InspectorWindow` 等。

### Tree Overview

```bash
u uitree dump -p "GameView"            # テキスト形式
u uitree dump -p "GameView" --json     # JSON形式
u uitree dump -p "GameView" -d 3       # 深さ3まで
```

各要素には `ref_N` の ID が付与される。

### Element Query

AND条件で組み合わせ可能:

```bash
u uitree query -p "GameView" -t Button              # タイプ
u uitree query -p "GameView" -n "StartBtn"           # 名前
u uitree query -p "GameView" -c "primary-button"     # USSクラス
u uitree query -p "GameView" -t Button -c "primary"  # 複合
```

### Detail Inspection

```bash
u uitree inspect ref_3                     # 基本情報
u uitree inspect ref_3 --style             # resolvedStyle 込み
u uitree inspect ref_3 --children          # 子要素込み
u uitree inspect ref_3 --style --children  # 両方
```

| フィールド | 内容 |
|-----------|------|
| type, name, classes | 要素の識別情報 |
| visible, enabledSelf | 表示/有効状態 |
| layout | ローカル座標 (x, y, width, height) |
| worldBound | グローバル座標 |
| resolvedStyle | 計算済みスタイル (--style 時) |
| children | 子要素リスト (--children 時) |

## Development Iteration Flow

UI の作成→Play 確認→修正を繰り返す開発サイクル。

```
Edit UI (UXML/USS/C#)
  │
  ▼
┌─────────────────────────────┐
│ Step 1: Compile & Play      │
│ u refresh                   │
│ u state (poll isCompiling)  │
│ u console get -l E          │
│ u play                      │
│ u state (poll isPlaying)    │
└──────────┬──────────────────┘
           ▼
      compile error? ──yes──► Fix & restart
           │
           no
           ▼
┌─────────────────────────────┐
│ Step 2: Visual Check        │
│ u uitree dump -p "GameView" │
│ u uitree query / inspect    │
│ u screenshot -s game        │
└──────────┬──────────────────┘
           ▼
┌─────────────────────────────┐
│ Step 3: User Feedback       │
│ スクリーンショットとツリー   │
│ 情報を提示しフィードバック待ち│
└──────────┬──────────────────┘
           ▼
      OK? ──yes──► u stop → Done
           │
           no
           ▼
      u stop → Edit → Step 1
```

### Step 1: Compile & Play

```bash
u refresh
u state          # isCompiling == false まで 2秒間隔ポーリング（最大30秒）
u console get -l E
```

コンパイルエラーがなければ:

```bash
u play
u state          # isPlaying == true まで（最大10秒）
```

### Step 2: Visual Check

Play Mode 中にUIの状態を確認:

```bash
u uitree dump -p "GameView" -d 3              # ツリー構造
u uitree query -p "GameView" -t Label         # 特定要素を検索
u uitree inspect ref_N --style                # スタイル詳細
u screenshot -s game -p ./ui_check.png        # スクリーンショット
```

### Step 3: User Feedback

スクリーンショットとツリー情報をユーザーに提示し、修正指示を待つ。自動修正は行わない。

修正が必要なら `u stop` で Play Mode を終了し、コードを修正して Step 1 に戻る。

## Investigation Patterns

### レイアウト問題

```bash
u uitree dump -p "GameView" -d 2
u uitree query -p "GameView" -c "broken-layout"
u uitree inspect ref_N --style
```

確認ポイント: width/height が 0、display: none、visibility: hidden。

### 要素が見つからない

```bash
u uitree query -p "GameView" -n "Button"     # 名前で広く
u uitree query -p "GameView" -t Button       # タイプで
u uitree dump -p "GameView" --json           # 全ツリー
```

### スタイル競合

```bash
u uitree inspect ref_N --style               # 対象
u uitree inspect ref_parent --style          # 親
u uitree inspect ref_sibling --style         # 兄弟
```

親の flex-direction, align-items, justify-content が子のレイアウトに影響していないか確認。

## Anti-Patterns

| パターン | 問題 | 対策 |
|---------|------|------|
| Play 中にコード修正 | 変更が反映されない | stop → 修正 → play |
| 毎回フルツリーダンプ | トークン浪費 | `-d 2` + query で絞り込む |
| --style を常時付与 | 出力が巨大 | 必要な時だけ |
| ref ID の再利用 | Play 再開で ID が変わる | Play ごとに再取得 |

## Token-Saving Strategies

| 状況 | 対応 |
|------|------|
| ツリーが巨大 | `-d 2` で浅く取得、必要部分だけ深掘り |
| JSON出力が冗長 | テキスト形式 (デフォルト) を使う |
| resolvedStyle が長い | 必要な時だけ `--style` を付ける |
| query結果が多い | 複合条件 (-t + -c) で絞り込む |
| イテレーション中 | 前回と差分がある部分だけ再検査 |

---

# uGUI (Canvas-based UI)

uGUI は Canvas をルートとするレガシーUI システム。unity-cli の component コマンドで検査・操作する。

## uGUI Inspection Flow

```
UI Issue / Layout Question (uGUI)
  │
  ▼
┌─────────────────────────────┐
│ Step 1: Find Canvas         │
│ u gameobject find           │
│   --name "Canvas"           │
│ u scene hierarchy -d 3      │
└──────────┬──────────────────┘
           ▼
┌─────────────────────────────┐
│ Step 2: List Components     │
│ u component list -t <obj>   │
└──────────┬──────────────────┘
           ▼
┌─────────────────────────────┐
│ Step 3: Inspect Properties  │
│ u component inspect -t <obj>│
│   -T Image / Text / Button  │
└──────────┬──────────────────┘
           ▼
      Analyze & Report
```

### Step 1: Canvas の発見

```bash
u gameobject find --name "Canvas"    # Canvas を検索
u scene hierarchy -d 3               # 上位3階層で UI 構造を把握
```

### Step 2: コンポーネント一覧

```bash
u component list -t "StartButton"    # オブジェクトのコンポーネント一覧
```

典型的な uGUI コンポーネント:
- `RectTransform`: 位置・サイズ
- `CanvasRenderer`: 描画
- `Image`: 画像表示
- `Text` / `TextMeshProUGUI`: テキスト表示
- `Button`: ボタン
- `Toggle`, `Slider`, `Dropdown`, `InputField`: 入力系

### Step 3: プロパティ検査

```bash
u component inspect -t "StartButton" -T Button
u component inspect -t "Title" -T Text
u component inspect -t "Background" -T Image
```

### uGUI プロパティ変更

```bash
# Image の色変更
u component modify -t "Background" -T Image --prop m_Color --value '{"r":1,"g":0,"b":0,"a":1}'

# Text の内容変更
u component modify -t "Title" -T Text --prop m_Text --value "New Title"

# RectTransform の位置変更
u component modify -t "Panel" -T RectTransform --prop m_AnchoredPosition --value '{"x":100,"y":50}'
```

### uGUI レイアウト問題の調査

```bash
# RectTransform を確認
u component inspect -t "Panel" -T RectTransform

# 確認ポイント
# - sizeDelta: サイズ
# - anchoredPosition: アンカー基準の位置
# - anchorMin / anchorMax: アンカー設定
# - pivot: ピボット
```

## uGUI Development Iteration Flow

```
Edit UI (Script / Inspector)
  │
  ▼
┌─────────────────────────────┐
│ Step 1: Compile & Play      │
│ u refresh                   │
│ u play                      │
└──────────┬──────────────────┘
           ▼
┌─────────────────────────────┐
│ Step 2: Visual Check        │
│ u scene hierarchy           │
│ u component inspect ...     │
│ u screenshot -s game        │
└──────────┬──────────────────┘
           ▼
┌─────────────────────────────┐
│ Step 3: User Feedback       │
│ スクリーンショット提示       │
└──────────┬──────────────────┘
           ▼
      OK? → u stop → Done
           ↓ no
      u stop → Edit → Step 1
```

## UI Toolkit vs uGUI 選択ガイド

| 条件 | 推奨 |
|------|------|
| 新規プロジェクト | UI Toolkit |
| エディタ拡張 | UI Toolkit |
| 既存 uGUI プロジェクト | uGUI 継続 |
| TextMeshPro 使用中 | uGUI |
| 複雑なレイアウト | UI Toolkit (Flexbox) |
| ランタイム性能重視 | uGUI (成熟度) |

## Related Skills

| スキル | 使い分け |
|--------|---------|
| /unity-preflight | UIコード修正後のコンパイルエラーが解決しない場合 |
| /unity-debug | UI操作時のランタイムエラー（NullRef等）を調査する場合 |
| /unity-scene | UI オブジェクトの配置・Transform 調整 |
