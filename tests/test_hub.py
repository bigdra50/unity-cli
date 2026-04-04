"""Tests for unity_cli/hub/ - Hub Package (paths, project, hub_cli, interactive)"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from unity_cli.exceptions import (
    HubInstallError,
    HubNotFoundError,
    ProjectError,
    ProjectVersionError,
)
from unity_cli.hub.hub_cli import HubCLI
from unity_cli.hub.interactive import is_tty, prompt_confirm, prompt_editor_selection
from unity_cli.hub.paths import InstalledEditor, PlatformPaths
from unity_cli.hub.project import (
    AssemblyDefinition,
    BuildScene,
    BuildSettings,
    PackageManifest,
    ProjectInfo,
    ProjectSettings,
    ProjectVersion,
    QualitySettings,
    TagLayerSettings,
    find_assembly_definitions,
    is_unity_project,
)

# =============================================================================
# ProjectVersion
# =============================================================================


class TestProjectVersion:
    """ProjectVersion のテスト"""

    def test_from_file_basic(self, tmp_path: Path) -> None:
        """基本的な ProjectVersion.txt のパース。"""
        (tmp_path / "ProjectSettings").mkdir()
        version_file = tmp_path / "ProjectSettings" / "ProjectVersion.txt"
        version_file.write_text("m_EditorVersion: 2022.3.10f1\n")

        sut = ProjectVersion.from_file(tmp_path)

        assert sut.version == "2022.3.10f1"
        assert sut.revision is None

    def test_from_file_with_revision(self, tmp_path: Path) -> None:
        """revision 情報付きのパース。"""
        (tmp_path / "ProjectSettings").mkdir()
        version_file = tmp_path / "ProjectSettings" / "ProjectVersion.txt"
        version_file.write_text("m_EditorVersion: 2022.3.10f1\nm_EditorVersionWithRevision: 2022.3.10f1 (abc123def)\n")

        sut = ProjectVersion.from_file(tmp_path)

        assert sut.version == "2022.3.10f1"
        assert sut.revision == "abc123def"

    def test_from_file_missing_raises(self, tmp_path: Path) -> None:
        """ファイルが存在しない場合 ProjectVersionError。"""
        with pytest.raises(ProjectVersionError, match="not found"):
            ProjectVersion.from_file(tmp_path)

    def test_from_file_invalid_format_raises(self, tmp_path: Path) -> None:
        """m_EditorVersion が含まれない不正フォーマット。"""
        (tmp_path / "ProjectSettings").mkdir()
        version_file = tmp_path / "ProjectSettings" / "ProjectVersion.txt"
        version_file.write_text("garbage content\n")

        with pytest.raises(ProjectVersionError, match="Invalid"):
            ProjectVersion.from_file(tmp_path)

    def test_frozen(self) -> None:
        """frozen=True で不変。"""
        sut = ProjectVersion(version="2022.3.10f1")
        with pytest.raises(AttributeError):
            sut.version = "2023.1.0f1"  # type: ignore[misc]


# =============================================================================
# is_unity_project
# =============================================================================


class TestIsUnityProject:
    """is_unity_project() のテスト"""

    def test_valid_project(self, tmp_path: Path) -> None:
        """Assets/ + ProjectSettings/ + ProjectVersion.txt が全て揃う場合。"""
        (tmp_path / "Assets").mkdir()
        ps = tmp_path / "ProjectSettings"
        ps.mkdir()
        (ps / "ProjectVersion.txt").write_text("m_EditorVersion: 2022.3.10f1")

        assert is_unity_project(tmp_path) is True

    def test_missing_assets(self, tmp_path: Path) -> None:
        """Assets/ がない場合。"""
        ps = tmp_path / "ProjectSettings"
        ps.mkdir()
        (ps / "ProjectVersion.txt").write_text("m_EditorVersion: 2022.3.10f1")

        assert is_unity_project(tmp_path) is False

    def test_missing_project_settings(self, tmp_path: Path) -> None:
        """ProjectSettings/ がない場合。"""
        (tmp_path / "Assets").mkdir()
        assert is_unity_project(tmp_path) is False

    def test_missing_version_file(self, tmp_path: Path) -> None:
        """ProjectVersion.txt がない場合。"""
        (tmp_path / "Assets").mkdir()
        (tmp_path / "ProjectSettings").mkdir()

        assert is_unity_project(tmp_path) is False

    def test_not_a_directory(self, tmp_path: Path) -> None:
        """パスがファイルの場合。"""
        file_path = tmp_path / "file.txt"
        file_path.write_text("test")
        assert is_unity_project(file_path) is False


# =============================================================================
# ProjectSettings
# =============================================================================


class TestProjectSettings:
    """ProjectSettings のテスト"""

    def test_from_file(self, tmp_path: Path) -> None:
        """ProjectSettings.asset のパース。"""
        (tmp_path / "ProjectSettings").mkdir()
        settings_file = tmp_path / "ProjectSettings" / "ProjectSettings.asset"
        settings_file.write_text(
            "productName: MyGame\n"
            "companyName: MyCorp\n"
            "bundleVersion: 1.0.0\n"
            "defaultScreenWidth: 1920\n"
            "defaultScreenHeight: 1080\n"
        )

        sut = ProjectSettings.from_file(tmp_path)

        assert sut.product_name == "MyGame"
        assert sut.company_name == "MyCorp"
        assert sut.version == "1.0.0"
        assert sut.default_screen_width == 1920
        assert sut.default_screen_height == 1080

    def test_from_file_missing_raises(self, tmp_path: Path) -> None:
        """ファイルが存在しない場合 ProjectError。"""
        with pytest.raises(ProjectError, match="not found"):
            ProjectSettings.from_file(tmp_path)

    def test_from_file_defaults_for_missing_keys(self, tmp_path: Path) -> None:
        """存在しないキーにはデフォルト値。"""
        (tmp_path / "ProjectSettings").mkdir()
        settings_file = tmp_path / "ProjectSettings" / "ProjectSettings.asset"
        settings_file.write_text("someOtherKey: value\n")

        sut = ProjectSettings.from_file(tmp_path)

        assert sut.product_name == "Unknown"
        assert sut.company_name == "Unknown"
        assert sut.version == "0.1"
        assert sut.default_screen_width == 1024
        assert sut.default_screen_height == 768


# =============================================================================
# BuildSettings
# =============================================================================


class TestBuildSettings:
    """BuildSettings のテスト"""

    def test_from_file_with_scenes(self, tmp_path: Path) -> None:
        """シーン情報のパース。"""
        (tmp_path / "ProjectSettings").mkdir()
        build_file = tmp_path / "ProjectSettings" / "EditorBuildSettings.asset"
        build_file.write_text(
            "m_Scenes:\n"
            "  - enabled: 1\n"
            "    path: Assets/Scenes/Main.unity\n"
            "  - enabled: 0\n"
            "    path: Assets/Scenes/Test.unity\n"
        )

        sut = BuildSettings.from_file(tmp_path)

        assert len(sut.scenes) == 2
        assert sut.scenes[0] == BuildScene(path="Assets/Scenes/Main.unity", enabled=True)
        assert sut.scenes[1] == BuildScene(path="Assets/Scenes/Test.unity", enabled=False)

    def test_from_file_missing_returns_empty(self, tmp_path: Path) -> None:
        """ファイルが存在しない場合は空リスト。"""
        sut = BuildSettings.from_file(tmp_path)
        assert sut.scenes == []


# =============================================================================
# PackageManifest
# =============================================================================


class TestPackageManifest:
    """PackageManifest のテスト"""

    def test_from_file(self, tmp_path: Path) -> None:
        """manifest.json のパース。"""
        (tmp_path / "Packages").mkdir()
        manifest = tmp_path / "Packages" / "manifest.json"
        manifest.write_text(
            json.dumps(
                {
                    "dependencies": {
                        "com.unity.textmeshpro": "3.0.6",
                        "com.example.local": "file:../local-pkg",
                        "com.unity.modules.audio": "1.0.0",
                    }
                }
            )
        )

        sut = PackageManifest.from_file(tmp_path)

        # modules はスキップ
        assert len(sut.dependencies) == 2
        names = [d.name for d in sut.dependencies]
        assert "com.unity.textmeshpro" in names
        assert "com.example.local" in names
        assert "com.unity.modules.audio" not in names

    def test_local_package_detection(self, tmp_path: Path) -> None:
        """file: プレフィックスのパッケージは is_local=True。"""
        (tmp_path / "Packages").mkdir()
        manifest = tmp_path / "Packages" / "manifest.json"
        manifest.write_text(
            json.dumps(
                {
                    "dependencies": {
                        "com.example.local": "file:../pkg",
                        "com.example.remote": "1.0.0",
                    }
                }
            )
        )

        sut = PackageManifest.from_file(tmp_path)

        local_pkg = next(d for d in sut.dependencies if d.name == "com.example.local")
        remote_pkg = next(d for d in sut.dependencies if d.name == "com.example.remote")
        assert local_pkg.is_local is True
        assert remote_pkg.is_local is False

    def test_from_file_missing_returns_empty(self, tmp_path: Path) -> None:
        """ファイルが存在しない場合は空リスト。"""
        sut = PackageManifest.from_file(tmp_path)
        assert sut.dependencies == []

    def test_sorted_by_name(self, tmp_path: Path) -> None:
        """パッケージ一覧は名前順にソート。"""
        (tmp_path / "Packages").mkdir()
        manifest = tmp_path / "Packages" / "manifest.json"
        manifest.write_text(
            json.dumps(
                {
                    "dependencies": {
                        "com.z.package": "1.0.0",
                        "com.a.package": "1.0.0",
                        "com.m.package": "1.0.0",
                    }
                }
            )
        )

        sut = PackageManifest.from_file(tmp_path)

        names = [d.name for d in sut.dependencies]
        assert names == sorted(names)


# =============================================================================
# TagLayerSettings
# =============================================================================


class TestTagLayerSettings:
    """TagLayerSettings のテスト"""

    def test_from_file_missing_returns_empty(self, tmp_path: Path) -> None:
        """ファイルが存在しない場合は空。"""
        sut = TagLayerSettings.from_file(tmp_path)
        assert sut.tags == []
        assert sut.layers == []
        assert sut.sorting_layers == []


# =============================================================================
# QualitySettings
# =============================================================================


class TestQualitySettings:
    """QualitySettings のテスト"""

    def test_from_file_missing_returns_default(self, tmp_path: Path) -> None:
        """ファイルが存在しない場合は current_quality=0, 空リスト。"""
        sut = QualitySettings.from_file(tmp_path)
        assert sut.current_quality == 0
        assert sut.levels == []


# =============================================================================
# AssemblyDefinition
# =============================================================================


class TestAssemblyDefinition:
    """AssemblyDefinition のテスト"""

    def test_from_file(self, tmp_path: Path) -> None:
        """asmdef ファイルのパース。"""
        asmdef = tmp_path / "Test.asmdef"
        asmdef.write_text(
            json.dumps(
                {
                    "name": "Game.Tests",
                    "references": ["UnityEngine.TestRunner"],
                    "includePlatforms": ["Editor"],
                    "excludePlatforms": [],
                    "allowUnsafeCode": True,
                    "autoReferenced": False,
                }
            )
        )

        sut = AssemblyDefinition.from_file(asmdef)

        assert sut.name == "Game.Tests"
        assert sut.references == ["UnityEngine.TestRunner"]
        assert sut.include_platforms == ["Editor"]
        assert sut.exclude_platforms == []
        assert sut.allow_unsafe is True
        assert sut.auto_referenced is False

    def test_from_file_defaults(self, tmp_path: Path) -> None:
        """最小限の asmdef (name のみ)。"""
        asmdef = tmp_path / "Minimal.asmdef"
        asmdef.write_text(json.dumps({"name": "Minimal"}))

        sut = AssemblyDefinition.from_file(asmdef)

        assert sut.name == "Minimal"
        assert sut.references == []
        assert sut.allow_unsafe is False
        assert sut.auto_referenced is True

    def test_from_file_no_name_uses_stem(self, tmp_path: Path) -> None:
        """name キーがない場合はファイル名を使用。"""
        asmdef = tmp_path / "FallbackName.asmdef"
        asmdef.write_text(json.dumps({}))

        sut = AssemblyDefinition.from_file(asmdef)
        assert sut.name == "FallbackName"


class TestFindAssemblyDefinitions:
    """find_assembly_definitions() のテスト"""

    def test_finds_asmdef_files(self, tmp_path: Path) -> None:
        """Assets/ 以下の .asmdef を検出。"""
        assets = tmp_path / "Assets"
        assets.mkdir()

        (assets / "A.asmdef").write_text(json.dumps({"name": "A"}))
        sub = assets / "Sub"
        sub.mkdir()
        (sub / "B.asmdef").write_text(json.dumps({"name": "B"}))

        result = find_assembly_definitions(tmp_path)

        names = [a.name for a in result]
        assert "A" in names
        assert "B" in names

    def test_sorted_by_name(self, tmp_path: Path) -> None:
        """結果は name 順にソート。"""
        assets = tmp_path / "Assets"
        assets.mkdir()

        (assets / "Z.asmdef").write_text(json.dumps({"name": "Z"}))
        (assets / "A.asmdef").write_text(json.dumps({"name": "A"}))

        result = find_assembly_definitions(tmp_path)
        names = [a.name for a in result]
        assert names == sorted(names)

    def test_no_assets_returns_empty(self, tmp_path: Path) -> None:
        """Assets/ がない場合は空リスト。"""
        result = find_assembly_definitions(tmp_path)
        assert result == []

    def test_invalid_json_skipped(self, tmp_path: Path) -> None:
        """不正な JSON の asmdef はスキップ。"""
        assets = tmp_path / "Assets"
        assets.mkdir()

        (assets / "Good.asmdef").write_text(json.dumps({"name": "Good"}))
        (assets / "Bad.asmdef").write_text("not json{{{")

        result = find_assembly_definitions(tmp_path)
        assert len(result) == 1
        assert result[0].name == "Good"


# =============================================================================
# ProjectInfo
# =============================================================================


class TestProjectInfo:
    """ProjectInfo のテスト"""

    @pytest.fixture
    def unity_project(self, tmp_path: Path) -> Path:
        """最小限の Unity プロジェクト構造を作成。"""
        (tmp_path / "Assets").mkdir()
        ps = tmp_path / "ProjectSettings"
        ps.mkdir()

        (ps / "ProjectVersion.txt").write_text("m_EditorVersion: 2022.3.10f1\n")
        (ps / "ProjectSettings.asset").write_text(
            "productName: TestGame\n"
            "companyName: TestCo\n"
            "bundleVersion: 1.0\n"
            "defaultScreenWidth: 1920\n"
            "defaultScreenHeight: 1080\n"
        )

        return tmp_path

    def test_from_path(self, unity_project: Path) -> None:
        """有効なプロジェクトから ProjectInfo を構築。"""
        sut = ProjectInfo.from_path(unity_project)

        assert sut.unity_version.version == "2022.3.10f1"
        assert sut.settings.product_name == "TestGame"

    def test_from_path_invalid_raises(self, tmp_path: Path) -> None:
        """無効なプロジェクトパスで ProjectError。"""
        with pytest.raises(ProjectError, match="Not a valid Unity project"):
            ProjectInfo.from_path(tmp_path)

    def test_to_dict(self, unity_project: Path) -> None:
        """to_dict が正しい形式を返す。"""
        sut = ProjectInfo.from_path(unity_project)
        d = sut.to_dict()

        assert d["unity_version"] == "2022.3.10f1"
        assert d["product_name"] == "TestGame"
        assert d["company_name"] == "TestCo"
        assert "screen_size" in d
        assert d["screen_size"]["width"] == 1920


# =============================================================================
# PlatformPaths / InstalledEditor dataclasses
# =============================================================================


class TestPlatformPaths:
    """PlatformPaths のテスト"""

    def test_frozen(self) -> None:
        sut = PlatformPaths(hub_cli=None, editor_base=Path("/tmp"))
        with pytest.raises(AttributeError):
            sut.hub_cli = Path("/new")  # type: ignore[misc]


class TestInstalledEditor:
    """InstalledEditor のテスト"""

    def test_frozen(self) -> None:
        sut = InstalledEditor(version="2022.3.10f1", path=Path("/tmp/Unity"))
        with pytest.raises(AttributeError):
            sut.version = "2023.1.0f1"  # type: ignore[misc]

    def test_values(self) -> None:
        sut = InstalledEditor(version="6000.0.0f1", path=Path("/Applications/Unity"))
        assert sut.version == "6000.0.0f1"
        assert sut.path == Path("/Applications/Unity")


# =============================================================================
# HubCLI
# =============================================================================


class TestHubCLI:
    """HubCLI のテスト"""

    def test_init_raises_when_hub_not_found(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Hub CLI が見つからない場合 HubNotFoundError。"""
        monkeypatch.setattr("unity_cli.hub.hub_cli.locate_hub_cli", lambda: None)
        with pytest.raises(HubNotFoundError, match="not found"):
            HubCLI()

    def test_init_with_explicit_path(self) -> None:
        """明示的パス指定で初期化。"""
        sut = HubCLI(hub_path=Path("/fake/hub"))
        assert sut._hub_path == Path("/fake/hub")

    def test_list_editors_parses_output(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """editors -i 出力をパース。"""
        sut = HubCLI(hub_path=Path("/fake/hub"))
        mock_result = MagicMock()
        mock_result.stdout = (
            "2022.3.10f1 , installed at /Applications/Unity/Hub/Editor/2022.3.10f1\n"
            "2023.1.0f1 , installed at /Applications/Unity/Hub/Editor/2023.1.0f1\n"
        )
        monkeypatch.setattr(sut, "_run_command", lambda args, timeout=300.0: mock_result)

        editors = sut.list_editors()

        assert len(editors) == 2
        assert editors[0].version == "2022.3.10f1"
        assert editors[1].version == "2023.1.0f1"

    def test_list_editors_empty_output(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """空出力なら空リスト。"""
        sut = HubCLI(hub_path=Path("/fake/hub"))
        mock_result = MagicMock()
        mock_result.stdout = ""
        monkeypatch.setattr(sut, "_run_command", lambda args, timeout=300.0: mock_result)

        assert sut.list_editors() == []

    def test_install_editor_raises_on_failure(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """インストール失敗時 HubInstallError。"""
        sut = HubCLI(hub_path=Path("/fake/hub"))
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "installation error"
        monkeypatch.setattr(sut, "_run_command", lambda args, timeout=3600.0: mock_result)

        with pytest.raises(HubInstallError, match="Failed to install"):
            sut.install_editor("2022.3.10f1")

    def test_install_editor_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """インストール成功時 True を返す。"""
        sut = HubCLI(hub_path=Path("/fake/hub"))
        mock_result = MagicMock()
        mock_result.returncode = 0
        monkeypatch.setattr(sut, "_run_command", lambda args, timeout=3600.0: mock_result)

        assert sut.install_editor("2022.3.10f1") is True

    def test_install_modules_raises_on_failure(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """モジュールインストール失敗時 HubInstallError。"""
        sut = HubCLI(hub_path=Path("/fake/hub"))
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "module error"
        monkeypatch.setattr(sut, "_run_command", lambda args, timeout=3600.0: mock_result)

        with pytest.raises(HubInstallError, match="Failed to install modules"):
            sut.install_modules("2022.3.10f1", ["ios"])


class TestHubCLIRunCommand:
    """HubCLI._run_command のテスト"""

    def test_timeout_raises_hub_install_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """subprocess タイムアウト時 HubInstallError。"""
        sut = HubCLI(hub_path=Path("/fake/hub"))
        monkeypatch.setattr(
            "subprocess.run",
            lambda *args, **kwargs: (_ for _ in ()).throw(subprocess.TimeoutExpired(args[0], 300)),
        )
        with pytest.raises(HubInstallError, match="timed out"):
            sut._run_command(["editors", "-i"])

    def test_file_not_found_raises_hub_not_found(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """バイナリが見つからない場合 HubNotFoundError。"""
        sut = HubCLI(hub_path=Path("/fake/hub"))
        monkeypatch.setattr(
            "subprocess.run",
            lambda *args, **kwargs: (_ for _ in ()).throw(FileNotFoundError()),
        )
        with pytest.raises(HubNotFoundError, match="not found"):
            sut._run_command(["editors", "-i"])


# =============================================================================
# Interactive
# =============================================================================


class TestIsTty:
    """is_tty() のテスト"""

    def test_returns_bool(self) -> None:
        """戻り値は bool。"""
        result = is_tty()
        assert isinstance(result, bool)


class TestPromptEditorSelection:
    """prompt_editor_selection() のテスト"""

    def test_returns_none_when_not_tty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """TTY でない場合 None を返す。"""
        monkeypatch.setattr("unity_cli.hub.interactive.is_tty", lambda: False)
        editors = [InstalledEditor(version="2022.3.10f1", path=Path("/tmp"))]

        result = prompt_editor_selection("2023.1.0f1", editors)
        assert result is None


class TestPromptConfirm:
    """prompt_confirm() のテスト"""

    def test_returns_default_when_not_tty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """TTY でない場合 default 値を返す。"""
        monkeypatch.setattr("unity_cli.hub.interactive.is_tty", lambda: False)

        assert prompt_confirm("question?", default=True) is True
        assert prompt_confirm("question?", default=False) is False
