# リファクタリング・機能強化 全体計画

最終更新: 2026-06-10

本ドキュメントは unity-cli コードベース(Python: `unity_cli/` + `relay/` 約 9,200 行 / C#: `UnityBridge/` 約 10,000 行)に蓄積した技術的負債の棚卸しと、フェーズ分割した解消・強化計画である。

---

## 1. 現状分析サマリ

### 1.1 負債インベントリ

| # | 負債 | 深刻度 | 規模 | 場所 |
|---|------|--------|------|------|
| D1 | プロトコル enum ドリフト: `idle` が C# 側 `ActivityPhase` に定義済みだが relay 側 `_VALID_DETAILS` に無く、警告付きで破棄される | **高** | 1 行 | `relay/server.py:47-55` / `UnityBridge/Editor/Protocol.cs:98` |
| D2 | C# Tool 19 ファイル全てで同一の引数パース・switch ディスパッチ・`ProtocolException` スロー・`JObject` レスポンス構築 (計 60〜80 箇所) を重複実装 | **高** | ~19 ファイル | `UnityBridge/Editor/Tools/*.cs` |
| D3 | `Response.cs` のヘルパー 4 クラス (`IBridgeResponse`/`SuccessResponse`/`ErrorResponse`/`PendingResponse`) が**完全未使用** | 中 | 115 行 | `UnityBridge/Editor/Helpers/Response.cs` |
| D4 | CLI コマンド 18+ ファイルで `if _should_json(...): print_json(...) else: print_*_table(...)` 分岐を 32+ 回重複 (~440 行) | **高** | 32 箇所 | `unity_cli/cli/commands/*.py` |
| D5 | エラーハンドリング二重スタイル: `@handle_cli_errors` デコレータ採用 7 ファイル vs inline try/except 12 ファイル | 中 | 19 ファイル | `unity_cli/cli/commands/*.py` |
| D6 | 巨大ファイル群 (責務混在): `UITree.cs` 1005 行 / `relay/server.py` 881 行 / `uitree.py` 796 行 / `Component.cs` 712 行 / `RelayServerLauncher.cs` 682 行 / `client.py` 660 行 / `RelayClient.cs` 634 行 / `output.py` 581 行 / `Tests.cs` 568 行 | **高** | ~6,500 行 | 上記 |
| D7 | テスト空白地帯: `relay/server.py` 実質 ~5% / C# Tools 15/19 が無テスト / CLI コマンド 9 ファイル (~1,315 行) 無テスト / API モジュール 3 ファイル無テスト | **高** | ~3,500 行 | `relay/`, `Tools/`, `cli/commands/` |
| D8 | Bridge スレッド同期がバグ多発地帯 (直近 40 コミット中に #105/#106/#110/#111 のスレッド系修正が集中)。`RelayClient.cs` の `_sendLock` 取得が 3 種類のタイムアウトポリシーで重複 | **高** | — | `UnityBridge/Editor/RelayClient.cs`, `BridgeManager.cs` |
| D9 | プロトコル定義の三重管理: `relay/protocol.py` / `Protocol.cs` / `docs/protocol-spec.md`。spec に STATUS detail の有効値一覧が無い。`AMBIGUOUS_INSTANCE` が C# 側に未定義 | 中 | 3 ファイル | 同上 |
| D10 | deprecated CLI オプション (`console --count/--filter/--verbose`) と後方互換エイリアス (`_sanitize_tsv` 等) の残存 | 低 | ~30 行 | `unity_cli/cli/commands/console.py:86-99`, `unity_cli/cli/output.py:169-189` |
| D11 | `output.py` で plain/rich 分岐 (`if console.no_color:`) を 11 関数で重複。テーブル定義が関数ごとにコピー | 中 | ~125 行 | `unity_cli/cli/output.py` |
| D12 | 型シリアライズ重複: Vector/Color/Quaternion 等の変換ロジックが `Component.cs` (360 行) と `UITree.cs` に散在 | 中 | ~400 行 | `Tools/Component.cs:297-656`, `Tools/UITree.cs:845-873` |
| D13 | `CommandDispatcher` の自動発見が assembly ロード失敗時に黙ってスキップ (Tool が静かに消える) | 中 | — | `UnityBridge/Editor/CommandDispatcher.cs:151-165` |
| D14 | CI に C# 静的解析が実質無い (ReSharper はライセンスゲートで無効)、Unity テストも CI 未実行 | 中 | — | `.github/workflows/csharp-inspect.yml` |
| D15 | 16 個の API クラスが同一の `__init__` + params 組み立てボイラープレート | 低 | ~150 行 | `unity_cli/api/*.py` |

### 1.2 健全な部分(壊さないこと)

- `pyproject.toml`: mypy strict / ruff (E,W,F,I,N,UP,B,C4,SIM) / import-linter による層契約 — **既に高水準。維持する**
- `relay/protocol.py`・`relay/instance_registry.py` はテスト充実 (テスト行数が実装を上回る)
- TestProject は `file:../../UnityBridge` 参照でコード複製なし
- バージョンは 2 箇所 (pyproject.toml / package.json) だが `scripts/bump-version.py` + CI ゲートで同期済み
- ドキュメント・README (en/jp) に大きなドリフトなし

---

## 2. 進め方の原則

1. **テストファースト** (CLAUDE.md 準拠): 各フェーズは「セーフティネットとなるテストを先に書く → リファクタ → グリーン確認 → コミット」の順
2. **挙動保存と機能強化を分離**: Phase 1〜5 は外部挙動 (CLI 出力・プロトコル・終了コード) を変えない。挙動変更は Phase 0 (バグ修正) と Phase 6 (強化) に隔離
3. **1 PR = 1 関心事**: フェーズ内の作業項目は独立 PR に分割可能な粒度で記述
4. **回帰検知の自動化**: リファクタ対象に触る前に、その領域の CI ゲート (テスト/lint/複雑度) を先に強化する

依存関係:

```
Phase 0 (即時修正) ──→ Phase 1 (セーフティネット) ──┬─→ Phase 2 (Python CLI)
                                                    ├─→ Phase 3 (Relay)
                                                    └─→ Phase 4 (C# Bridge)
Phase 2〜4 完了 ──→ Phase 5 (プロトコル単一情報源化) ──→ Phase 6 (機能強化)
```

Phase 2/3/4 は相互依存が薄く並行着手可能。

---

## Phase 0: 即時修正と死蔵コード削除(挙動修正・小)

**目的**: 調査で確定した実バグと完全な死蔵コードを先に片付け、以降のリファクタのノイズを消す。

| 作業 | 対象 | 内容 |
|------|------|------|
| 0-1 | `relay/server.py:47-55` | `_VALID_DETAILS` に `"idle"` を追加 (D1)。再現テスト: C# `ActivityPhase` の全値が relay で受理されることを検証するテストを `tests/` に追加 (RED→GREEN) |
| 0-2 | `UnityBridge/Editor/Protocol.cs` | `AMBIGUOUS_INSTANCE` エラーコードの要否を判断: C# 側が受信し得るなら定義追加、CLI 専用なら spec にその旨明記 (D9) |
| 0-3 | `docs/protocol-spec.md` | STATUS `detail` の有効値一覧テーブルを追記 (D9) |
| 0-4 | `UnityBridge/Editor/Helpers/Response.cs` | 削除 — ただし Phase 4 でレスポンスビルダーを再設計するため、**設計を流用するか確認の上**で削除 or 改修 (D3) |
| 0-5 | `unity_cli/cli/output.py:169-189` | 後方互換エイリアス `_sanitize_tsv` / `_print_plain_table` を参照元ごと整理して削除 (D10) |
| 0-6 | `unity_cli/cli/commands/console.py` | deprecated オプション (`--count/--filter/--verbose`) の削除を次のメジャー/マイナーリリースで実施。今フェーズでは削除予定バージョンを警告文に明記 (D10) |
| 0-7 | `RelayServerLauncher.cs:76-80` | 書き込みのみで読まれない `CustomCommand` EditorPrefs の削除 or 機能完成の判断 |

**受け入れ基準**: 全 pytest グリーン / `u -i TestProject refresh` → コンパイルエラーなし / `idle` 受理テストが追加されている。

**規模感**: 小 (1〜2 PR)。

---

## Phase 1: セーフティネット構築(テスト・CI 強化)

**目的**: リファクタ対象の挙動を固定するテストを先に整備する (D7, D13, D14)。**このフェーズではプロダクションコードを原則変更しない** (テスト容易化のための最小限の seam 追加のみ許可)。

### 1-A. relay/server.py の挙動固定 (最優先)

- `asyncio` ベースの relay サーバー結合テストを追加: フェイク Unity (TCP で REGISTER/STATUS/COMMAND_RESULT/PONG を喋るスタブ) + フェイク CLI クライアントを `tests/` 内に実装
- 固定する挙動: REGISTER→READY 遷移 / COMMAND→BUSY→READY / beforeReload→RELOADING→afterReload 復帰 / heartbeat タイムアウト切断 / RELOADING 30s 延長タイムアウト / idempotency キャッシュ / Single Outstanding PING
- 目標: `relay/server.py` の主要分岐をカバー (現状 ~5% → 60%+)

### 1-B. CLI コマンド層のテスト

- `typer.testing.CliRunner` + `UnityClient` モックで、無テストの 9 コマンドファイル (`project.py`, `screenshot.py`, `recorder.py`, `asset.py`, `editor_control.py`, `editor_hub.py`, `config.py`, `completion.py`, `open_cmd.py`) にスモークテストを追加
- 固定する挙動: JSON 出力モード時の出力スキーマ / 終了コード / 必須引数欠落時のエラー
- API モジュール 3 ファイル (`api/asset.py`, `api/recorder.py`, `api/screenshot.py`) に送信 params を検証する単体テストを追加

### 1-C. C# Bridge のテスト土台

- `TestProject/Assets/Tests/Editor/` に **Tool 網羅テスト**を追加: リフレクションで `[BridgeTool]` 全クラスを列挙し、(a) 登録されること、(b) 未知 action で `InvalidParams` を返すこと、を全 Tool に対して機械的に検証 (D13 の検知網)
- `CommandDispatcher` の assembly ロード失敗を「警告ログ + 失敗 Tool 名の記録」に強化し、テストで検証
- 無テスト 15 Tools のうち、Phase 4 で分割予定の `UITree.cs` / `Component.cs` / `Tests.cs` / `Screenshot.cs` / `Recorder.cs` を優先して現行挙動の特性テスト (characterization test) を追加

### 1-D. CI 強化

- プロトコル整合性チェックスクリプト (`scripts/check-protocol-consistency.py`) を新設: `relay/protocol.py` の MessageType/ErrorCode/detail 値と `Protocol.cs` の定数を正規表現抽出で突き合わせ、差異で CI を fail させる (D1 の再発防止, D9)
- pytest にカバレッジ計測 (`pytest-cov`) を追加し、CI で `relay/` と `unity_cli/` のカバレッジを可視化 (まずは閾値なし、Phase 2 以降で閾値導入)
- C# はライセンス不要の静的解析へ移行検討: `dotnet format` の verify + Roslyn Analyzer (Microsoft.CodeAnalysis.NetAnalyzers) を CI のデフォルトに (D14)。ReSharper はオプション維持

**受け入れ基準**: server.py カバレッジ 60%+ / 全 CLI コマンドにスモークテスト / Tool 網羅テスト導入 / プロトコル整合性チェックが CI で稼働。

**規模感**: 大 (4〜6 PR)。**ここが計画全体の投資の中心**。以降のフェーズの安全性はこのフェーズの質に比例する。

---

## Phase 2: Python CLI レイヤのリファクタ(挙動保存)

**目的**: D4, D5, D11, D15 の重複を構造で解消し、`uitree.py` / `client.py` / `output.py` の責務を分離する。

### 2-A. 出力レイヤの抽象化 (D4, D11)

1. `unity_cli/cli/output.py` を `unity_cli/cli/output/` パッケージに分割:
   - `console.py` — コンソール/モード管理 (quiet/verbose/no_color のグローバル状態を `OutputContext` に集約)
   - `renderers.py` — `render(data, *, table_spec, fields)` 単一エントリポイント。JSON / rich table / plain TSV の出し分けを**ここ 1 箇所**に集約
   - `tables.py` — エンティティごとのカラム定義 (`TableSpec` 宣言) のみを持つ。plain/rich 分岐は持たない
2. コマンド側の `if _should_json(...): ... else: ...` 32 箇所を `render()` 呼び出し 1 行に置換 (~440 行削減見込み)
3. `print_json` のフィールドフィルタ引数の渡し方を統一 (D4.2)

### 2-B. エラーハンドリング統一 (D5)

- 全 19 コマンドファイルを `@handle_cli_errors` デコレータに統一。inline try/except + `_handle_error()` 12 ファイルを移行
- ruff カスタムルールが使えないため、`tests/` に「commands 配下の全 typer コマンド関数がデコレータを持つ」ことを AST で検査するテストを追加して固定

### 2-C. バリデーション共通化 (D1.1 系)

- `unity_cli/cli/helpers.py` に `require_name_or_id(name, id, *, what: str)` を追加し、component/gameobject/asset の 10 箇所の重複バリデーションを置換

### 2-D. API クライアント層の整理 (D15, client.py 分割)

1. `unity_cli/client.py` (660 行) を分割:
   - `unity_cli/transport.py` — TCP フレーミング・低レベル send/recv (現 154-224 行付近)
   - `unity_cli/connection.py` — リトライ/バックオフ/request_id 管理 (現 227-320 行付近)
   - `unity_cli/client.py` — `UnityClient` ファサードのみ残す
2. `unity_cli/api/` に `BaseApi` を導入: `self._send(action, **params)` が None 値の除去と `send_request` 呼び出しを共通化。各 API メソッドは params の宣言だけになる
3. import-linter 契約を新レイヤ構成 (`transport ← connection ← api ← cli`) に合わせて更新

### 2-E. 巨大コマンドファイルの分割

- `unity_cli/cli/commands/uitree.py` (796 行) → `uitree/` サブパッケージへ: `dump.py` / `query.py` / `interact.py` / `monkey.py` / `snapshot.py` (Typer サブアプリで結合)
- `unity_cli/cli/commands/project.py` (419 行) → Hub 系と Editor 系で分割を検討
- `unity_cli/hub/project.py` (440 行) → パーサごと (`project_version.py` / `build_settings.py` / `quality_settings.py`) に分割

**受け入れ基準**: 全 pytest グリーン / Phase 1-B で固定した JSON 出力・終了コードのスナップショットが不変 / radon/xenon の複雑度ゲート通過 / import-linter 契約グリーン / コマンドファイル平均行数 50% 減。

**規模感**: 大 (5〜7 PR)。2-A → 2-B → 2-C は順に、2-D / 2-E は並行可。

---

## Phase 3: Relay サーバーのリファクタ(挙動保存)

**目的**: `relay/server.py` (881 行) の責務分離 (D6)。Phase 1-A のテストを命綱にする。

1. 分割案:
   - `relay/server.py` — エントリポイント・接続受付のみ (~150 行)
   - `relay/unity_session.py` — Unity 1 接続のメッセージルーティング (REGISTER/STATUS/COMMAND_RESULT/PONG) と状態遷移
   - `relay/client_session.py` — CLI クライアント要求 (REQUEST/LIST_INSTANCES/SET_DEFAULT) のルーティング
   - `relay/heartbeat.py` — heartbeat ループ・Single Outstanding PING・タイムアウト管理
   - `relay/dispatch.py` — instance 解決 + コマンド転送 + idempotency キャッシュ参照
2. 状態遷移 (DISCONNECTED/READY/BUSY/RELOADING) を `instance_registry.py` 側の明示的なステートマシン (許可遷移テーブル) に寄せ、server 側の ad-hoc な状態書き換えを排除
3. `instance_registry.py` (517 行) から queue 管理と ref ID 追跡を別モジュールへ (既存テスト 950 行を活かしてリファクタ)
4. 無効化されている queue 機能 (FIFO max 10, disabled by default) の**存廃判断**: 使う計画が無ければ削除して複雑度を下げる。残すなら Phase 6 で有効化+テスト

**受け入れ基準**: Phase 1-A の結合テスト全グリーン / 実機確認 (`u state`, domain reload を挟んだ `u refresh`) / 各新モジュール 300 行以下。

**規模感**: 中〜大 (3〜4 PR)。

---

## Phase 4: C# Bridge のリファクタ(挙動保存)

**目的**: D2, D3, D6, D8, D12 の解消。スレッド系バグ多発地帯の構造的解決を含む、C# 側の本丸。

### 4-A. Tool 共通基盤 (D2, D3)

1. `BridgeToolBase` (または action ルータヘルパー) を導入:
   - `action` 抽出 + `ToLowerInvariant` switch + 未知 action エラーを基盤側へ (19 ファイルの重複排除)
   - `RequireString(parameters, "name")` / `RequireNameOrId(...)` 等のパラメータ抽出ヘルパーで `ProtocolException` スローを共通化
2. レスポンスビルダー導入: `BridgeResponse.Ok(message).With("path", path)` 形式の fluent ビルダーを新設し、60〜80 箇所の手書き `JObject` を置換。死蔵 `Response.cs` は本設計で置き換えて削除
3. Tool 1 つ (例: `Asset.cs`) をパイロット移行 → Phase 1-C のテストで挙動不変を確認 → 残り 18 Tools を機械的に移行

### 4-B. シリアライズ統合 (D12)

- `UnityBridge/Editor/Helpers/ValueSerializer.cs` を新設: Vector2/3/Quaternion/Color/Enum/ObjectReference のパース・シリアライズを `Component.cs:297-656` から抽出し、`UITree.cs` のスタイルシリアライズもここへ寄せる
- `Component.cs` の Transform/Camera 特殊ケース (661-710 行) を `ComponentSerializers/` として分離

### 4-C. 巨大 Tool の分割 (D6)

| 元ファイル | 分割後 |
|-----------|--------|
| `UITree.cs` (1005 行) | `UITree/PanelDiscovery.cs` (リフレクションによるパネル列挙) / `UITree/TreeSerializer.cs` / `UITree/ElementQuery.cs` / `UITree/ElementInteraction.cs` / `UITree/RefIdRegistry.cs` |
| `Component.cs` (712 行) | 4-B 抽出後に ~300 行へ縮小見込み。残りは listing / modification に二分 |
| `Tests.cs` (568 行) | `TestRunnerAdapter.cs` (TestRunnerApi ラップ) / `TestResultStore.cs` (静的状態の集約) / `Tests.cs` (コマンドハンドラのみ) |
| `Screenshot.cs` (443 行) / `Recorder.cs` (499 行) | キャプチャ共通処理を `CaptureHelpers.cs` へ統合 (既存ファイルあり、寄せ切る) |

### 4-D. スレッド同期の構造化 (D8) — **最重要**

直近の修正履歴 (#105, #106, #110, #111, コミット 3674681 / 3c89d59) はいずれも「背景スレッド→メインスレッドのディスパッチ」「`_sendLock` の競合」「heartbeat と送信の干渉」が根因。個別パッチの積み増しを止め、構造で解決する:

1. **設計ドキュメント先行**: `docs/bridge-threading-design.md` を新設し、スレッド境界 (受信ループ / メインスレッド / 送信) と各データの所有権を明文化。過去 4 issue の根因を整理して反映
2. **単一送信キュー化**: `RelayClient.cs` の 3 種類のタイムアウト付き `_sendLock` 取得 (CommandResult / Status / Pong) を、優先度付き単一送信キュー + 1 送信ループに置換。「PONG はドロップ可」「STATUS は最新のみ保持」「COMMAND_RESULT は必達」のポリシーをキュー側で表現し、ロックタイムアウトのハンドチューニングを廃止
3. **メインスレッドディスパッチャの共通化**: `EditorApplication.update` 登録パターンを `MainThreadDispatcher` ヘルパーに集約し、`BridgeManager.cs` のコメント頼みの順序制約をコードで保証
4. `Tests.cs` の static 可変状態 (`_testRunnerApi`, `_activeCollector`, `_lastCompletedResult`) を 4-C の `TestResultStore` に集約し、domain reload を跨ぐ生存戦略 (SessionState) を明示

### 4-E. RelayServerLauncher 分割

- `RelayServerLauncher.cs` (682 行) → プロセス管理 / パス検出 (uv tool・ローカル dev 判定) / 状態永続化 (SessionState/EditorPrefs) の 3 分割

**受け入れ基準**: `u -i TestProject tests run edit` 全グリーン / Phase 1-C の Tool 網羅テスト・特性テストグリーン / domain reload 復帰の実機確認 / `RelayClient` のロックタイムアウト定数 (PongLockTimeoutMs 等) が消滅。

**規模感**: 大 (6〜8 PR)。4-A → (4-B, 4-C 並行) → 4-D の順。4-D は単独 PR + 実機検証を厚めに。

---

## Phase 5: プロトコルの単一情報源化(構造強化)

**目的**: D9 の三重管理を「スキーマ 1 箇所 + 生成/検証」に転換し、ドリフトの再発を構造的に防ぐ。

1. `protocol/schema.json` (または YAML) を新設: MessageType / ErrorCode / ActivityPhase(detail) / 各メッセージの必須フィールドを宣言
2. 選択肢の比較検討の上で実装 (推奨は **(a)**):
   - **(a) 検証アプローチ**: Phase 1-D のチェックスクリプトをスキーマ駆動に昇格。Python/C# の手書き定義をスキーマと突合して CI で fail。実装コスト小・既存コード不変
   - (b) 生成アプローチ: スキーマから `protocol.py` / `Protocol.cs` の定数部を生成。ドリフト原理的にゼロだがビルド複雑化
3. `docs/protocol-spec.md` の enum 表をスキーマから自動生成 (または CI で照合)
4. バージョン情報の単一情報源化: 現状の 2 ファイル + 同期スクリプト + CI ゲートは実用上十分なため、**優先度低のまま維持**。hatch の dynamic version 等への移行は任意

**受け入れ基準**: enum をどれか 1 実装にだけ追加すると CI が fail することをテストで実証。

**規模感**: 小〜中 (1〜2 PR)。

---

## Phase 6: 機能強化

**目的**: 構造が整った後にしか安全にやれない強化を実施。各項目は独立に取捨選択可能。

| # | 強化 | 内容 | 依存 |
|---|------|------|------|
| 6-1 | **Unity テストの CI 実行** | GameCI (game-ci/unity-test-runner) + Unity Personal ライセンスで TestProject の EditMode テストを PR CI に組み込む。Phase 1-C/4 で増えた C# テストの回帰検知が自動化される | Phase 1-C |
| 6-2 | **コマンドキューの正式化 or 削除** | Phase 3-4 の存廃判断に従い、残す場合: BUSY 時の自動キューイングを opt-in → デフォルト有効化し、`u --no-queue` を追加 | Phase 3 |
| 6-3 | **`unity_cli` の非同期 API 公開** | `transport`/`connection` 分離 (Phase 2-D) を土台に asyncio 版クライアントを提供。複数インスタンス並列操作 (`u --all refresh` 等) を可能に | Phase 2-D |
| 6-4 | **deprecated オプションの削除断行** | Phase 0-6 で予告したバージョンで `console --count/--filter/--verbose` を削除 | Phase 0 |
| 6-5 | **出力フォーマット拡張** | Phase 2-A の renderer 集約により、`--output yaml` / `--output ndjson` 追加が renderer 1 箇所の変更で可能に | Phase 2-A |
| 6-6 | **C# 静的解析の常時化** | Roslyn Analyzer ベースラインを整備し、新規警告ゼロを PR ゲート化 | Phase 1-D |
| 6-7 | **プロトコルスキーマの公開** | Phase 5 のスキーマを外部ツール (他言語クライアント) 向けに docs へ公開 | Phase 5 |

---

## 7. 全体ロードマップとリスク

| フェーズ | 規模 | 並行性 | 主リスク | 緩和策 |
|---------|------|--------|---------|--------|
| 0 即時修正 | 小 | — | ほぼ無し | — |
| 1 セーフティネット | **大** | 1-A/B/C/D 並行可 | テスト自体が現行バグを仕様として固定する | バグ疑い箇所は issue 化して特性テストに `# known-issue` を明記 |
| 2 Python CLI | 大 | 2-D/E 並行可 | 出力フォーマットの意図せぬ変化 | Phase 1-B のスナップショットテストで検知 |
| 3 Relay | 中〜大 | Phase 2 と並行可 | 状態遷移・タイムアウトの挙動変化 | Phase 1-A の結合テスト + 実機 domain reload 検証 |
| 4 C# Bridge | **大** | Phase 2/3 と並行可 | 4-D のスレッド変更による新規 race | 設計 doc 先行 / 単一 PR / 実機長時間テスト (heartbeat 数百サイクル) |
| 5 単一情報源化 | 小〜中 | — | 過剰設計 (codegen) | 検証アプローチ (a) を既定とする |
| 6 機能強化 | 項目次第 | 項目ごと独立 | — | — |

### 効果の見込み (定量)

- 重複削減: Python ~600 行 / C# ~800 行相当のボイラープレート消滅
- 最大ファイル: 1005 行 (`UITree.cs`) → 全ファイル 400 行以下
- テスト空白: `relay/server.py` ~5%→60%+、C# Tools 無テスト 15/19 → 網羅テスト + 主要 Tool 特性テスト
- ドリフト再発: プロトコル enum / エラーコードの追加漏れが CI で機械検知
- バグ多発地帯 (Bridge スレッド同期) がポリシー明示の単一送信キューに置換され、タイムアウト・ハンドチューニングが消滅

---

## 8. 着手順のまとめ(最初の 5 PR)

1. **PR-1** (Phase 0): `idle` 修正 + 整合性テスト + spec への detail 表追記
2. **PR-2** (Phase 0): 死蔵コード削除 (`Response.cs` 判断含む) + deprecated 警告へ削除予定明記
3. **PR-3** (Phase 1-A): relay 結合テスト基盤 (フェイク Unity/CLI スタブ) + 状態遷移テスト
4. **PR-4** (Phase 1-D): プロトコル整合性チェックスクリプト + CI 組み込み + pytest-cov
5. **PR-5** (Phase 1-B): CLI コマンドスモークテスト一式

以降は Phase 2-A (出力レイヤ) と Phase 1-C (C# テスト土台) を並行で進めるのが最短経路。
