---
name: unity-router
description: Unity 開発に関する質問を適切なスキルへルーティングする
invocation: urouter
triggers:
  - unity-router
  - urouter
  - Unity routing
  - どのスキル
---

# Unity Router

Unity 開発に関する質問を分析し、適切なスキルまたはエージェントへルーティングする。

## ルーティングテーブル

### Layer 2: ワークフロースキル

| キーワード | スキル | 用途 |
|-----------|--------|------|
| コンパイル, テスト, 検証, verify, test | /unity-preflight | Refresh→Compile→Test 実行 |
| エラー, バグ, 調査, debug, exception | /unity-debug | エラー調査・分類・分析 |
| ビルド, build, apk, aab, player | /unity-build | ビルドパイプライン |
| シーン, scene, hierarchy, gameobject配置 | /unity-scene | シーン構築・編集 |
| アセット, asset, prefab, 依存関係, deps | /unity-asset | アセット管理・依存調査 |
| パフォーマンス, 最適化, profiler, fps | /unity-perf | プロファイラ実行・分析 |
| UI, VisualElement, Canvas, uGUI, UXML | /unity-ui | UI 検査・開発 |

### エラーコード → スキルマッピング

| エラーパターン | スキル |
|--------------|--------|
| CS0029, CS0030, CS0266 (型変換) | /unity-debug |
| CS0103, CS0246, CS0234 (名前解決) | /unity-debug |
| CS1061, CS0117 (メンバー不明) | /unity-debug |
| CS0120, CS0176 (static/instance混同) | /unity-debug |
| NullReferenceException | /unity-debug |
| MissingReferenceException | /unity-debug |
| MissingComponentException | /unity-debug |

### エージェント

| 必要な情報 | エージェント |
|-----------|------------|
| API ドキュメント, ソースコード参照 | unity-guide |
| Unity バージョン, LTS 情報 | version-checker |

## ルーティングプロセス

```
1. 質問を分析
   ↓
2. キーワードを識別
   ↓
3. 該当スキル/エージェントを特定
   ↓
4. 複数該当する場合は優先順位で決定
   - エラー調査系 > ワークフロー系
   - 具体的 > 汎用的
   ↓
5. スキルを読み込み、指示に従う
```

## 優先順位

1. エラー調査 (/unity-debug) - CS コード、例外名がある場合
2. 検証 (/unity-preflight) - テスト・コンパイル確認が必要な場合
3. ビルド (/unity-build) - ビルド関連の場合
4. シーン (/unity-scene) - シーン構築・GameObject 操作の場合
5. アセット (/unity-asset) - アセット管理・依存関係の場合
6. UI (/unity-ui) - UI 開発の場合
7. パフォーマンス (/unity-perf) - 最適化・プロファイリングの場合

## 使用例

```
Q: "CS0246 エラーが出ています"
→ Layer 1 シグナル検出 → /unity-debug

Q: "ビルドが通らない"
→ ビルド + エラー → /unity-debug 優先 (エラー調査が先)
→ 解決後 → /unity-build

Q: "シーンにオブジェクトを配置したい"
→ /unity-scene

Q: "Transform の使い方を教えて"
→ API 詳細 → unity-guide エージェント

Q: "FPS が低い、重い"
→ /unity-perf
```

## 複合ケース

質問が複数のスキルにまたがる場合:

1. 主要な問題を特定
2. 順序を決定（例: 調査 → 修正 → 検証）
3. 各フェーズで適切なスキルを使用

```
Q: "ビルドエラーを直してテストを通したい"
→ 1. /unity-debug (エラー調査・修正)
→ 2. /unity-preflight (テスト実行)
→ 3. /unity-build (ビルド実行)
```
