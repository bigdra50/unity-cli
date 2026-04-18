"""Tests for unity_cli/exceptions.py - Exception Hierarchy"""

from __future__ import annotations

import pytest

from unity_cli.exceptions import (
    ConnectionError,
    EditorNotFoundError,
    HubError,
    HubInstallError,
    HubNotFoundError,
    InstanceError,
    ProjectError,
    ProjectVersionError,
    ProtocolError,
    TimeoutError,
    UnityCLIError,
)


class TestUnityCLIError:
    """UnityCLIError 基底クラスのテスト"""

    def test_message_only(self) -> None:
        """メッセージのみ指定時、code は None。"""
        sut = UnityCLIError("something went wrong")
        assert sut.message == "something went wrong"
        assert sut.code is None

    def test_message_with_code(self) -> None:
        """メッセージとコードの両方を指定。"""
        sut = UnityCLIError("fail", code="E001")
        assert sut.message == "fail"
        assert sut.code == "E001"

    def test_str_without_code(self) -> None:
        """code なしの str 表現はメッセージのみ。"""
        sut = UnityCLIError("plain message")
        assert str(sut) == "plain message"

    def test_str_with_code(self) -> None:
        """code ありの str 表現は [code] message 形式。"""
        sut = UnityCLIError("detail", code="ERR_X")
        assert str(sut) == "[ERR_X] detail"

    def test_is_exception(self) -> None:
        """Exception を継承している。"""
        assert issubclass(UnityCLIError, Exception)

    def test_can_be_raised_and_caught(self) -> None:
        """raise/except で動作する。"""
        with pytest.raises(UnityCLIError, match="test"):
            raise UnityCLIError("test")


class TestInheritanceHierarchy:
    """例外クラスの継承階層テスト"""

    @pytest.mark.parametrize(
        ("child", "parent"),
        [
            (ConnectionError, UnityCLIError),
            (ProtocolError, UnityCLIError),
            (InstanceError, UnityCLIError),
            (TimeoutError, UnityCLIError),
            (HubError, UnityCLIError),
            (HubNotFoundError, HubError),
            (HubInstallError, HubError),
            (ProjectError, UnityCLIError),
            (ProjectVersionError, ProjectError),
            (EditorNotFoundError, ProjectError),
        ],
    )
    def test_subclass_relationship(self, child: type, parent: type) -> None:
        """各例外は正しい親クラスを継承。"""
        assert issubclass(child, parent)

    @pytest.mark.parametrize(
        "exc_cls",
        [
            ConnectionError,
            ProtocolError,
            InstanceError,
            TimeoutError,
            HubError,
            HubNotFoundError,
            HubInstallError,
            ProjectError,
            ProjectVersionError,
            EditorNotFoundError,
        ],
    )
    def test_all_inherit_from_base(self, exc_cls: type) -> None:
        """全例外が UnityCLIError を継承。"""
        assert issubclass(exc_cls, UnityCLIError)


class TestSubclassBehavior:
    """サブクラスが UnityCLIError の振る舞いを継承するテスト"""

    @pytest.mark.parametrize(
        ("exc_cls", "code"),
        [
            (ConnectionError, "CONN_REFUSED"),
            (ProtocolError, "PROTOCOL_ERR"),
            (InstanceError, "INSTANCE_NOT_FOUND"),
            (TimeoutError, "TIMEOUT"),
            (HubNotFoundError, "HUB_NOT_FOUND"),
            (HubInstallError, "HUB_INSTALL_FAILED"),
            (ProjectVersionError, "PROJECT_VERSION_NOT_FOUND"),
            (EditorNotFoundError, "EDITOR_NOT_FOUND"),
        ],
    )
    def test_subclass_with_code(self, exc_cls: type[UnityCLIError], code: str) -> None:
        """サブクラスも code 付きで生成可能。"""
        sut = exc_cls("msg", code=code)
        assert sut.code == code
        assert str(sut) == f"[{code}] msg"

    def test_catch_hub_error_catches_hub_not_found(self) -> None:
        """HubError で catch すると HubNotFoundError もキャッチされる。"""
        with pytest.raises(HubError):
            raise HubNotFoundError("hub missing", code="HUB_NOT_FOUND")

    def test_catch_project_error_catches_version_error(self) -> None:
        """ProjectError で catch すると ProjectVersionError もキャッチされる。"""
        with pytest.raises(ProjectError):
            raise ProjectVersionError("version file missing")

    def test_catch_base_catches_all(self) -> None:
        """UnityCLIError で catch すると全サブクラスをキャッチ。"""
        with pytest.raises(UnityCLIError):
            raise EditorNotFoundError("not installed")
