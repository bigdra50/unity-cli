"""Tests for unity_cli/config.py - Configuration Module"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from unity_cli.config import (
    CONFIG_FILE_NAME,
    DEFAULT_RELAY_HOST,
    DEFAULT_RELAY_PORT,
    DEFAULT_TIMEOUT_MS,
    HEADER_SIZE,
    MAX_PAYLOAD_BYTES,
    PROTOCOL_VERSION,
    UnityCLIConfig,
)


class TestProtocolConstants:
    """プロトコル定数の確認"""

    def test_protocol_version(self) -> None:
        assert PROTOCOL_VERSION == "1.0"

    def test_default_relay_host(self) -> None:
        assert DEFAULT_RELAY_HOST == "127.0.0.1"

    def test_default_relay_port(self) -> None:
        assert DEFAULT_RELAY_PORT == 6500

    def test_header_size(self) -> None:
        assert HEADER_SIZE == 4

    def test_max_payload_bytes(self) -> None:
        assert MAX_PAYLOAD_BYTES == 16 * 1024 * 1024

    def test_default_timeout_ms(self) -> None:
        assert DEFAULT_TIMEOUT_MS == 30000

    def test_config_file_name(self) -> None:
        assert CONFIG_FILE_NAME == ".unity-cli.toml"


class TestUnityCLIConfigDefaults:
    """UnityCLIConfig デフォルト値のテスト"""

    def test_default_relay_host(self) -> None:
        sut = UnityCLIConfig()
        assert sut.relay_host == "127.0.0.1"

    def test_default_relay_port(self) -> None:
        sut = UnityCLIConfig()
        assert sut.relay_port == 6500

    def test_default_timeout(self) -> None:
        sut = UnityCLIConfig()
        assert sut.timeout == 15.0

    def test_default_timeout_ms(self) -> None:
        sut = UnityCLIConfig()
        assert sut.timeout_ms == 30000

    def test_default_instance_is_none(self) -> None:
        sut = UnityCLIConfig()
        assert sut.instance is None

    def test_default_retry_initial_ms(self) -> None:
        sut = UnityCLIConfig()
        assert sut.retry_initial_ms == 500

    def test_default_retry_max_ms(self) -> None:
        sut = UnityCLIConfig()
        assert sut.retry_max_ms == 8000

    def test_default_retry_max_time_ms(self) -> None:
        sut = UnityCLIConfig()
        assert sut.retry_max_time_ms == 45000


class TestUnityCLIConfigValidation:
    """UnityCLIConfig バリデーションのテスト"""

    @pytest.mark.parametrize(
        "port",
        [0, -1, 65536, 100000],
        ids=["zero", "negative", "65536", "large"],
    )
    def test_invalid_relay_port(self, port: int) -> None:
        """範囲外のポート番号は ValidationError。"""
        with pytest.raises(ValidationError):
            UnityCLIConfig(relay_port=port)

    @pytest.mark.parametrize(
        "port",
        [1, 6500, 65535],
        ids=["min", "default", "max"],
    )
    def test_valid_relay_port(self, port: int) -> None:
        """有効なポート番号。"""
        sut = UnityCLIConfig(relay_port=port)
        assert sut.relay_port == port

    def test_timeout_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            UnityCLIConfig(timeout=0)

    def test_timeout_ms_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            UnityCLIConfig(timeout_ms=0)

    def test_retry_initial_ms_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            UnityCLIConfig(retry_initial_ms=0)

    def test_retry_max_ms_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            UnityCLIConfig(retry_max_ms=0)

    def test_retry_max_time_ms_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            UnityCLIConfig(retry_max_time_ms=0)

    def test_extra_fields_ignored(self) -> None:
        """extra='ignore' により未知フィールドは無視。"""
        sut = UnityCLIConfig(unknown_field="value")  # type: ignore[call-arg]
        assert not hasattr(sut, "unknown_field")

    def test_validate_assignment(self) -> None:
        """validate_assignment=True: 代入時もバリデーション。"""
        sut = UnityCLIConfig()
        with pytest.raises(ValidationError):
            sut.relay_port = 0


class TestUnityCLIConfigLoad:
    """UnityCLIConfig.load() のテスト"""

    def test_load_from_toml_file(self, tmp_path: Path) -> None:
        """TOML ファイルから設定を読み込む。"""
        config_file = tmp_path / CONFIG_FILE_NAME
        config_file.write_text('relay_host = "192.168.1.100"\nrelay_port = 7000\ntimeout = 30.0\ntimeout_ms = 60000\n')

        sut = UnityCLIConfig.load(config_file)

        assert sut.relay_host == "192.168.1.100"
        assert sut.relay_port == 7000
        assert sut.timeout == 30.0
        assert sut.timeout_ms == 60000

    def test_load_partial_toml(self, tmp_path: Path) -> None:
        """部分的な TOML ファイルは指定分だけ上書き、残りはデフォルト。"""
        config_file = tmp_path / CONFIG_FILE_NAME
        config_file.write_text("relay_port = 9999\n")

        sut = UnityCLIConfig.load(config_file)

        assert sut.relay_port == 9999
        assert sut.relay_host == DEFAULT_RELAY_HOST  # default

    def test_load_nonexistent_file_returns_defaults(self) -> None:
        """存在しないファイルパスはデフォルト値を返す。"""
        sut = UnityCLIConfig.load(Path("/nonexistent/path/config.toml"))
        assert sut.relay_host == DEFAULT_RELAY_HOST
        assert sut.relay_port == DEFAULT_RELAY_PORT

    def test_load_none_returns_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """config_path=None かつ _find_config_file が None を返す場合、デフォルト。"""
        monkeypatch.setattr(UnityCLIConfig, "_find_config_file", classmethod(lambda cls: None))
        sut = UnityCLIConfig.load(None)
        assert sut.relay_port == DEFAULT_RELAY_PORT

    def test_load_invalid_toml_returns_defaults(self, tmp_path: Path) -> None:
        """不正な TOML ファイルはデフォルト値を返す。"""
        config_file = tmp_path / CONFIG_FILE_NAME
        config_file.write_text("this is not valid toml {{{{")

        sut = UnityCLIConfig.load(config_file)

        assert sut.relay_port == DEFAULT_RELAY_PORT

    def test_load_with_instance(self, tmp_path: Path) -> None:
        """instance フィールドの読み込み。"""
        config_file = tmp_path / CONFIG_FILE_NAME
        config_file.write_text('instance = "/path/to/project"\n')

        sut = UnityCLIConfig.load(config_file)

        assert sut.instance == "/path/to/project"

    def test_load_extra_fields_ignored(self, tmp_path: Path) -> None:
        """未知フィールドは無視される。"""
        config_file = tmp_path / CONFIG_FILE_NAME
        config_file.write_text('some_unknown = "value"\nrelay_port = 8000\n')

        sut = UnityCLIConfig.load(config_file)

        assert sut.relay_port == 8000


class TestUnityCLIConfigToToml:
    """UnityCLIConfig.to_toml() のテスト"""

    def test_to_toml_contains_all_fields(self) -> None:
        """生成される TOML に全フィールドが含まれる。"""
        sut = UnityCLIConfig()
        toml_str = sut.to_toml()

        assert 'relay_host = "127.0.0.1"' in toml_str
        assert "relay_port = 6500" in toml_str
        assert "timeout = 15.0" in toml_str
        assert "timeout_ms = 30000" in toml_str
        assert "retry_initial_ms = 500" in toml_str
        assert "retry_max_ms = 8000" in toml_str
        assert "retry_max_time_ms = 45000" in toml_str

    def test_to_toml_instance_not_set(self) -> None:
        """instance=None の場合 '# not set' がコメント出力される。"""
        sut = UnityCLIConfig()
        toml_str = sut.to_toml()
        assert "instance = # not set" in toml_str

    def test_to_toml_instance_set(self) -> None:
        """instance が設定されている場合、引用符付きで出力。"""
        sut = UnityCLIConfig(instance="/my/project")
        toml_str = sut.to_toml()
        assert 'instance = "/my/project"' in toml_str

    def test_to_toml_roundtrip(self, tmp_path: Path) -> None:
        """to_toml で書き出した文字列を load で読み込み、値が一致する。"""
        original = UnityCLIConfig(
            relay_host="10.0.0.1",
            relay_port=7777,
            timeout=20.0,
            timeout_ms=50000,
            instance="/project",
            retry_initial_ms=1000,
            retry_max_ms=16000,
            retry_max_time_ms=90000,
        )
        config_file = tmp_path / CONFIG_FILE_NAME
        config_file.write_text(original.to_toml())

        loaded = UnityCLIConfig.load(config_file)

        assert loaded.relay_host == original.relay_host
        assert loaded.relay_port == original.relay_port
        assert loaded.timeout == original.timeout
        assert loaded.timeout_ms == original.timeout_ms
        assert loaded.retry_initial_ms == original.retry_initial_ms
        assert loaded.retry_max_ms == original.retry_max_ms
        assert loaded.retry_max_time_ms == original.retry_max_time_ms
