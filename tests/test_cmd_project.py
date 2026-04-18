"""Tests for unity_cli/cli/commands/project.py - Project CLI Commands

project サブコマンドは Relay 不要（ファイルベース）なので、
CliRunner でテストしやすい。ただし、main callback が UnityClient を
生成しようとするため、relay_host へ接続不要な project コマンドでも
callback を通る必要がある。ここでは UnityClient を mock に差し替えて
テストする。
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from unity_cli.cli.app import app

runner = CliRunner()


@pytest.fixture
def unity_project(tmp_path: Path) -> Path:
    """最小限の Unity プロジェクト構造を作成。"""
    (tmp_path / "Assets").mkdir()
    ps = tmp_path / "ProjectSettings"
    ps.mkdir()

    (ps / "ProjectVersion.txt").write_text(
        "m_EditorVersion: 2022.3.10f1\nm_EditorVersionWithRevision: 2022.3.10f1 (abc123)\n"
    )
    (ps / "ProjectSettings.asset").write_text(
        "productName: TestGame\n"
        "companyName: TestCo\n"
        "bundleVersion: 1.2.3\n"
        "defaultScreenWidth: 1920\n"
        "defaultScreenHeight: 1080\n"
    )

    pkgs = tmp_path / "Packages"
    pkgs.mkdir()
    (pkgs / "manifest.json").write_text(
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

    return tmp_path


def _invoke(args: list[str]) -> object:
    """UnityClient の生成を mock してから CliRunner.invoke を実行。

    main callback 内で `from unity_cli.client import UnityClient` が
    ローカル import されるため、unity_cli.client.UnityClient を patch する。
    """
    with patch("unity_cli.client.UnityClient", return_value=MagicMock()):
        return runner.invoke(app, args)


class TestProjectVersion:
    """project version コマンドのテスト"""

    def test_shows_version(self, unity_project: Path) -> None:
        """Unity バージョンが表示される。"""
        result = _invoke(["project", "version", str(unity_project)])
        assert result.exit_code == 0
        assert "2022.3.10f1" in result.output

    def test_json_output(self, unity_project: Path) -> None:
        """--json でJSON形式の出力。"""
        result = _invoke(["project", "version", str(unity_project), "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["version"] == "2022.3.10f1"
        assert data["revision"] == "abc123"

    def test_invalid_path(self, tmp_path: Path) -> None:
        """無効なパスでエラー。"""
        result = _invoke(["project", "version", str(tmp_path)])
        assert result.exit_code != 0


class TestProjectInfo:
    """project info コマンドのテスト"""

    def test_shows_info(self, unity_project: Path) -> None:
        """プロジェクト情報が表示される。"""
        result = _invoke(["project", "info", str(unity_project)])
        assert result.exit_code == 0
        assert "TestGame" in result.output
        assert "TestCo" in result.output

    def test_json_output(self, unity_project: Path) -> None:
        """--json でJSON形式の出力。"""
        result = _invoke(["project", "info", str(unity_project), "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["product_name"] == "TestGame"
        assert data["unity_version"] == "2022.3.10f1"

    def test_invalid_path(self, tmp_path: Path) -> None:
        """無効なパスでエラー。"""
        result = _invoke(["project", "info", str(tmp_path)])
        assert result.exit_code != 0


class TestProjectPackages:
    """project packages コマンドのテスト"""

    def test_lists_packages(self, unity_project: Path) -> None:
        """パッケージ一覧が表示される。"""
        result = _invoke(["project", "packages", str(unity_project)])
        assert result.exit_code == 0
        assert "textmeshpro" in result.output

    def test_json_output(self, unity_project: Path) -> None:
        """--json でJSON形式の出力。"""
        result = _invoke(["project", "packages", str(unity_project), "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        names = [pkg["name"] for pkg in data]
        assert "com.unity.textmeshpro" in names
        # modules はデフォルトで除外
        assert "com.unity.modules.audio" not in names

    def test_include_modules(self, unity_project: Path) -> None:
        """--include-modules でモジュールも含まれる。"""
        result = _invoke(["project", "packages", str(unity_project), "--include-modules", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        names = [pkg["name"] for pkg in data]
        assert "com.unity.modules.audio" in names

    def test_invalid_path(self, tmp_path: Path) -> None:
        """無効なパスでエラー。"""
        result = _invoke(["project", "packages", str(tmp_path)])
        assert result.exit_code != 0
