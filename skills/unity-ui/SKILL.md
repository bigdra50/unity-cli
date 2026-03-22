---
name: unity-ui
description: |
  UI 開発・検査・自動テストワークフロー。uitree で構造把握→pytest E2E テスト生成→PlayMode テストに移植。
  Use for: "UI確認", "UI Toolkit", "uGUI", "E2Eテスト", "UI操作", "uitree", "スクリーンショット"
user-invocable: true
metadata:
  openclaw:
    category: "game-development"
    requires:
      bins: ["u"]
---

# unity-ui

> **PREREQUISITE:** `../unity-shared/SKILL.md`
>
> uitree コマンドは Play Mode 中のみ動作する。必ず `u play` してから実行すること。

## UI テストの種別

| 種別 | 検証内容 | 手法 | スクショ |
|------|---------|------|---------|
| Functional | 操作→状態が正しいか | click → text で値検証 | 不要 |
| Visual Regression | 外観が変わっていないか | screenshot → 画像比較 | 必要 |
| Structural Snapshot | ツリー構造が変わっていないか | dump --json → diff | 不要 |
| Smoke | 最低限動くか | click → console にエラーなし | 任意 |

## UI システム判定

| 手がかり | UI Toolkit | uGUI |
|---------|-----------|------|
| ファイル | `.uxml`, `.uss` | `.prefab` に Canvas |
| コンポーネント | UIDocument | Canvas, RectTransform |

## コマンドリファレンス

要素の指定方法は2通り: ref ID (`ref_3`) または `-p <panel> -n <name>`。

### 構造把握

```bash
u uitree dump                           # 全パネル一覧 (contextType: Player がゲーム側)
u uitree dump -p "PanelSettings"        # パネルのツリー (各要素の ref/name/type/classes が見える)
u uitree dump -p "PanelSettings" --json # JSON 出力 (snapshot用)
u uitree query -p "PanelSettings" -t Button              # type で検索 (VisualElement ベースのボタンはヒットしない → -c で検索)
u uitree query -p "PanelSettings" -n "BtnStart"          # name で検索
u uitree query -p "PanelSettings" -c "action-btn"        # USS class で検索
u uitree query -p "PanelSettings" -t Button -c "primary" # AND 条件
u uitree inspect -p "PanelSettings" -n "BtnStart"        # 要素詳細
u uitree inspect ref_5_48                                # ref ID で指定
u uitree inspect ref_5_48 --style                        # resolvedStyle 含む
u uitree inspect ref_5_48 --children                     # 子要素情報含む
```

### テキスト取得

```bash
u uitree text -p "PanelSettings" -n "ToastMessage"  # name で指定
u uitree text ref_5_12                               # ref ID で指定
```

### 操作

```bash
u uitree click -p "PanelSettings" -n "BtnContinue"  # name で指定
u uitree click ref_5_48                              # ref ID で指定
u uitree click ref_5_48 --count 2                    # ダブルクリック
u uitree click ref_5_48 --button 1                   # 右クリック
u uitree scroll -p "PanelSettings" -n "ScrollArea" --y 100
```

### スクリーンショット

```bash
u screenshot                          # GameView (-s game がデフォルト)
u screenshot -p "ui-check.png"        # 保存先指定
u screenshot --burst -n 5             # 連続 (アニメーション確認)
```

UI Toolkit / uGUI (Screen Space) は `-s game` でのみ映る。`-s camera` では映らない。

GameView のキャプチャにはエディタのフォーカスが必要。タイムアウトする場合は再試行で解決することが多い。

### uGUI の場合

uitree は UI Toolkit 専用。uGUI は scene/component コマンドで操作する。

```bash
u scene hierarchy --depth 3
u component list -t "Canvas"
u component inspect -t "MyButton" -T "UnityEngine.UI.Button"
```

## 開発→テストフロー

```text
Phase 1: 作成 & 手動確認
  コード変更 → /unity-verify → play → dump → 操作 → screenshot → stop

Phase 2: pytest E2E テスト生成
  dump で構造把握 → pytest テストファイルを生成 → 実行して確認

Phase 3: PlayMode テスト移植
  安定したシナリオを C# に書き直す → CI で回帰テスト
```

### Phase 1: 作成 & 手動確認

```bash
u play
u uitree dump -p "PanelSettings"                 # 構造把握
u uitree click -p "PanelSettings" -n "BtnStart"  # 操作
u uitree text -p "PanelSettings" -n "StatusLabel" # 状態確認
u screenshot                                      # 結果キャプチャ
u stop
```

### Phase 2: pytest E2E テスト生成

Phase 1 で確認した操作シナリオを、pytest テストとして永続化する。
unity-cli の Python API (`UITreeAPI`, `ConsoleAPI`, `EditorAPI`) を直接使う。

手順:
1. `u play` + `u uitree dump` で構造を把握する
2. 操作可能な要素（ボタン名、ラベル名）を特定する
3. 以下のテンプレートに従い、`tests/integration/` にテストファイルを生成する
4. `uv run python -m pytest tests/integration/<file> -v` で実行して確認する

テンプレート:

```python
"""E2E tests for <UI名> — pytest + unity-cli API."""
import time
import pytest
from unity_cli.api import ConsoleAPI, EditorAPI, UITreeAPI
from unity_cli.client import RelayConnection

PANEL = "<パネル名>"  # u uitree dump で確認したパネル名


@pytest.fixture(scope="module")
def conn() -> RelayConnection:
    conn = RelayConnection(instance="<プロジェクト名>", timeout=5.0)
    try:
        EditorAPI(conn).get_state()
    except Exception:
        pytest.skip("Relay not available")
    return conn


@pytest.fixture(scope="module")
def uitree(conn: RelayConnection) -> UITreeAPI:
    return UITreeAPI(conn)


@pytest.fixture(scope="module")
def console(conn: RelayConnection) -> ConsoleAPI:
    return ConsoleAPI(conn)


@pytest.fixture(scope="module")
def editor(conn: RelayConnection) -> EditorAPI:
    return EditorAPI(conn)


@pytest.fixture(autouse=True)
def _play_mode(editor: EditorAPI):
    """Play Mode に入る。"""
    state = editor.get_state()
    if not state.get("isPlaying"):
        editor.play()
        deadline = time.time() + 10
        while time.time() < deadline:
            if editor.get_state().get("isPlaying"):
                break
            time.sleep(0.5)
    yield


@pytest.fixture(scope="module", autouse=True)
def _stop_after_all(editor: EditorAPI):
    """全テスト後に Play Mode 終了。"""
    yield
    try:
        editor.stop()
    except Exception:
        pass


# --- Functional テスト ---

class TestMenuButtons:
    def test_continue_shows_toast(self, uitree: UITreeAPI) -> None:
        uitree.click(panel=PANEL, name="<ボタン名>")
        time.sleep(0.3)
        result = uitree.text(panel=PANEL, name="<ラベル名>")
        assert result["text"] == "<期待値>"


# --- Smoke テスト ---

class TestSmoke:
    BUTTONS = ["<ボタン1>", "<ボタン2>", ...]

    def test_all_clickable_without_errors(self, uitree: UITreeAPI, console: ConsoleAPI) -> None:
        console.clear()
        for btn in self.BUTTONS:
            uitree.click(panel=PANEL, name=btn)
            time.sleep(0.2)
        errors = console.get(types=["error"])
        assert errors.get("entries", []) == []


# --- Structural Snapshot ---

class TestStructure:
    def test_tab_switch_changes_tree(self, uitree: UITreeAPI) -> None:
        before = uitree.dump(panel=PANEL)
        uitree.click(panel=PANEL, name="<タブ名>")
        time.sleep(0.3)
        after = uitree.dump(panel=PANEL)
        assert before != after
```

既存の `conftest.py` に `conn`, `uitree`, `editor`, `console` fixture がある場合はテンプレートの fixture 定義を省略し、conftest に委譲する。fixture の scope は conftest に合わせる（conftest が `session` なら `_play_mode` 等も同じ scope か互換性のある scope にする）。

動的な値（タイムスタンプ、プログレス%等）を持つラベルは等値比較ではなくフォーマット検証を使う:
```python
assert result["text"].endswith("%")  # "65%" 等
```

テストの種別に応じてクラスを追加する:
- `TestMenuButtons` — Functional (click → text 検証)
- `TestSmoke` — 全ボタンクリック + エラーなし
- `TestStructure` — ツリー構造の変化検出
- `TestVisual` — screenshot 撮影（画像比較は手動 or 別ツール）

### Phase 3: PlayMode テスト移植

Phase 2 の pytest で安定したシナリオを C# PlayMode テストに書き直す。

PlayMode に移植する基準:
- CI で毎回回す回帰テスト
- フレーム精度が必要 (アニメーション完了待ち等)
- Assert で厳密に状態検証
- InputSystem / EventSystem 経由の操作

pytest E2E のまま残す基準:
- 探索的テスト (シナリオが毎回変わる)
- AI エージェントの自律テスト
- Unity 外からの結合テスト

手順:
1. Phase 2 の pytest テストから安定したシナリオを選ぶ
2. 以下のテンプレートに従い、`Assets/Tests/PlayMode/` に C# テストを生成する
3. asmdef に UI コントローラの参照を追加する（必要に応じて）
4. `u tests run play` で実行して確認する

テンプレート:

```csharp
using System.Collections;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;
using UnityEngine.UIElements;

namespace Game.Tests.PlayMode
{
    [TestFixture]
    public class <UI名>Tests
    {
        private GameObject _hudObject;
        private UIDocument _uiDocument;
        private VisualElement _root;

        [UnitySetUp]
        public IEnumerator SetUp()
        {
            // UIDocument を持つ GameObject を生成
            // コントローラが Awake/OnEnable で初期化するのを待つ
            _hudObject = new GameObject("TestHUD");
            _hudObject.AddComponent<<コントローラ名>>();
            _uiDocument = _hudObject.GetComponent<UIDocument>();

            // コルーチン初期化 (StartCoroutine in OnEnable 等) は1フレームでは完了しない
            // 2フレーム以上待つ
            yield return null;
            yield return null;

            _root = _uiDocument.rootVisualElement;
            Assert.IsNotNull(_root, "Root visual element should be initialized");
        }

        [TearDown]
        public void TearDown()
        {
            Object.Destroy(_hudObject);
        }

        // --- Functional テスト ---

        [UnityTest]
        public IEnumerator <ボタン名>_Shows<期待される動作>()
        {
            var btn = _root.Q("<ボタン名>");
            Assert.IsNotNull(btn);

            Click(btn);
            yield return null;

            var label = _root.Q<Label>("<ラベル名>");
            Assert.AreEqual("<期待値>", label.text);
        }

        // --- Smoke テスト ---

        [UnityTest]
        public IEnumerator AllButtons_ClickableWithoutErrors()
        {
            var buttons = new[] { "<ボタン1>", "<ボタン2>", ... };

            foreach (var name in buttons)
            {
                var element = _root.Q(name);
                Assert.IsNotNull(element, $"{name} should exist");
                Click(element);
                yield return null;
            }

            LogAssert.NoUnexpectedReceived();
        }

        // --- ヘルパー ---

        private static void Click(VisualElement element)
        {
            using var evt = ClickEvent.GetPooled();
            evt.target = element;
            element.panel.visualTree.SendEvent(evt);
        }
    }
}
```

Click ヘルパーの注意:
- `ClickEvent.GetPooled()` で座標計算不要のイベントを生成し、`panel.visualTree.SendEvent` で発火する
- `NavigationSubmitEvent` では `RegisterCallback<ClickEvent>` が反応しないため使わない
- ホバーやプレスエフェクトも再現したい場合は `PointerDownEvent` + `PointerUpEvent` を `worldBound.center` 座標付きで送る

asmdef の注意:
- テスト対象クラスが `Assembly-CSharp`（asmdef なし）にある場合、テスト asmdef からは直接参照できない
- 対象クラスに専用 asmdef を作成し、テスト asmdef の `references` に追加する
- 例: `Assets/UI/Game.UI.asmdef` を作成 → `Game.Tests.PlayMode.asmdef` の references に `"Game.UI"` を追加

Phase 2 の pytest テストの各テストメソッドを1対1で C# に移植する。

移植後は `u tests run play` で実行。

## CLI 非対応操作

unity-shared のフォールバック順に従う:
1. `u api schema --type <Type>` で対応メソッドを検索
2. `u api call` で実行
3. 該当なしの場合のみ YAML 直接編集
