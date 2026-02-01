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
| コンパイル, テスト, 検証, verify, test | /uverify | Refresh→Compile→Test 実行 |
| エラー, バグ, 調査, debug, exception | /udebug | エラー調査・分類・分析 |
| ビルド, build, apk, aab, player | /ubuild | ビルドパイプライン |
| シーン, scene, hierarchy, gameobject配置 | /uscene | シーン構築・編集 |
| アセット, asset, prefab, 依存関係, deps | /uasset | アセット管理・依存調査 |
| パフォーマンス, 最適化, profiler, fps | /uperf | プロファイラ実行・分析 |
| UI, VisualElement, Canvas, uGUI, UXML | /uui | UI 検査・開発 |

### エラーコード → スキルマッピング

| エラーパターン | スキル |
|--------------|--------|
| CS0029, CS0030, CS0266 (型変換) | /udebug |
| CS0103, CS0246, CS0234 (名前解決) | /udebug |
| CS1061, CS0117 (メンバー不明) | /udebug |
| CS0120, CS0176 (static/instance混同) | /udebug |
| NullReferenceException | /udebug |
| MissingReferenceException | /udebug |
| MissingComponentException | /udebug |

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

1. エラー調査 (/udebug) - CS コード、例外名がある場合
2. 検証 (/uverify) - テスト・コンパイル確認が必要な場合
3. ビルド (/ubuild) - ビルド関連の場合
4. シーン (/uscene) - シーン構築・GameObject 操作の場合
5. アセット (/uasset) - アセット管理・依存関係の場合
6. UI (/uui) - UI 開発の場合
7. パフォーマンス (/uperf) - 最適化・プロファイリングの場合

## 使用例

```
Q: "CS0246 エラーが出ています"
→ Layer 1 シグナル検出 → /udebug

Q: "ビルドが通らない"
→ ビルド + エラー → /udebug 優先 (エラー調査が先)
→ 解決後 → /ubuild

Q: "シーンにオブジェクトを配置したい"
→ /uscene

Q: "Transform の使い方を教えて"
→ API 詳細 → unity-guide エージェント

Q: "FPS が低い、重い"
→ /uperf
```

## 複合ケース

質問が複数のスキルにまたがる場合:

1. 主要な問題を特定
2. 順序を決定（例: 調査 → 修正 → 検証）
3. 各フェーズで適切なスキルを使用

```
Q: "ビルドエラーを直してテストを通したい"
→ 1. /udebug (エラー調査・修正)
→ 2. /uverify (テスト実行)
→ 3. /ubuild (ビルド実行)
```
