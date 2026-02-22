# Recipes

unity-cli はUnixツールと組み合わせて使うことを前提に設計されている。
各コマンドはstdout/stderrを分離し、パイプに適した出力を行う。

## 目次

- [スクリーンショット](#スクリーンショット)
- [コンソールログ](#コンソールログ)
- [シーン・Hierarchy](#シーンhierarchy)
- [JSON出力とjq](#json出力とjq)
- [終了コードの活用](#終了コードの活用)
- [監視・定点観測](#監視定点観測)
- [CI / スクリプト](#ci--スクリプト)

---

## スクリーンショット

パイプ時は自動的にファイルパスのみをstdoutに出力する。

### ターミナルでインライン表示

```bash
u screenshot -s game | mcat -i
```

### クリップボードにコピー

```bash
# macOS: パスをクリップボードに
u screenshot -s game | pbcopy

# 画像自体をクリップボードに
u screenshot -s game | xargs -I{} osascript -e 'set the clipboard to (read (POSIX file "{}") as TIFF picture)'
```

### デフォルトビューアで開く

```bash
u screenshot -s game | xargs open
```

### スクショを撮ってSlackに投げる

```bash
u screenshot -s game -p /tmp/ss.png && slack-cli upload /tmp/ss.png -c "#dev"
```

### 連続キャプチャ

```bash
for i in $(seq 1 5); do
  u screenshot -s game -p "/tmp/frame_${i}.png"
  sleep 1
done
```

---

## コンソールログ

`u console get` の出力はプレーンテキスト。Unix標準ツールでそのままフィルタできる。

### エラーだけ直近10件

```bash
u console get -l E | head -10
```

### NullRefのスタックトレースを確認

```bash
u console get -s | grep -A5 "NullRef"
```

### エラー件数をカウント

```bash
u console get -l E | wc -l
```

### 特定パターンを除外

```bash
u console get -l W | grep -v "deprecated"
```

### ログをファイルに保存

```bash
u console get -s > "console_$(date +%Y%m%d_%H%M%S).log"
```

### JSON形式でjq処理

```bash
# messageフィールドだけ抽出
u console get --json | jq -r '.entries[].message'

# Error以上のログのタイムスタンプとメッセージ
u console get --json | jq -r '.entries[] | select(.type >= 2) | "\(.timestamp) \(.message)"'
```

---

## シーン・Hierarchy

### Hierarchyをfzfで検索

```bash
u scene hierarchy --depth 3 | fzf
```

### JSON形式でオブジェクト名だけ抽出

```bash
u scene hierarchy --depth 2 --json | jq -r '.items[].name'
```

### 特定名のオブジェクトがシーンにあるか確認

```bash
u scene hierarchy --depth 5 | grep -q "Player" && echo "found" || echo "not found"
```

---

## JSON出力とjq

`--json` フラグはサブコマンドごとのオプション。コマンド末尾に付ける。

### インスタンス一覧からプロジェクトパスだけ取得

```bash
u instances --json | jq -r '.[].instance_id'
```

### コンポーネントのプロパティ値を取得

```bash
u component inspect -t "Player" -T Transform --json | jq '.position'
```

### パッケージ名とバージョンをTSV出力

```bash
u project packages . --json | jq -r '.[] | [.name, .version] | @tsv'
```

---

## 終了コードの活用

| コード | 意味 |
|--------|------|
| 0 | 成功 |
| 2 | リトライ可能（リロード中など） |
| 3 | Relay未接続 |
| 5 | テスト失敗あり |

### 接続チェック

```bash
u state > /dev/null 2>&1 && echo "connected" || echo "disconnected"
```

### テスト結果で分岐

```bash
if u tests run edit; then
  echo "All tests passed"
else
  u console get -l E
fi
```

---

## 監視・定点観測

### エラーログを定期監視

```bash
watch -n5 'u console get -l E | tail -5'
```

### Play中のFPSを監視（Profiler）

```bash
watch -n2 'u profiler snapshot | grep -i fps'
```

---

## CI / スクリプト

### コンパイル確認 → テスト → エラーチェック

```bash
u refresh && u tests run edit && u console get -l E
```

### テスト実行してSlack通知

```bash
if u tests run edit 2>/dev/null; then
  curl -X POST "$SLACK_WEBHOOK" -d '{"text":"Tests passed"}'
else
  ERRORS=$(u console get -l E | head -5)
  curl -X POST "$SLACK_WEBHOOK" -d "{\"text\":\"Tests failed:\n${ERRORS}\"}"
fi
```

### 全インスタンスの状態確認

```bash
u instances --json | jq -r '.[].instance_id' | while read -r path; do
  echo "--- $path ---"
  u -i "$path" state
done
```

---

## 連携ツール

| ツール | 用途 | 例 |
|--------|------|-----|
| `mcat -i` | ターミナル画像表示 | `u screenshot \| mcat -i` |
| `jq` | JSON加工 | `u instances --json \| jq ...` |
| `fzf` | インタラクティブ選択 | `u scene hierarchy \| fzf` |
| `grep` | テキストフィルタ | `u console get \| grep "Error"` |
| `head`/`tail` | 件数制限 | `u console get \| head -10` |
| `watch` | 定期実行 | `watch -n5 'u console get -l E'` |
| `xargs` | パイプの値を引数に | `u screenshot \| xargs open` |
| `pbcopy` | クリップボード | `u screenshot \| pbcopy` |
| `wc` | カウント | `u console get -l E \| wc -l` |
