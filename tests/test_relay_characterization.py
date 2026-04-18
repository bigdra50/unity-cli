"""Characterization tests for relay/ package.

Freeze current behavior and constants to detect unintended changes
during refactoring.
"""

from __future__ import annotations

import pytest

from relay.instance_registry import QUEUE_ENABLED, QUEUE_MAX_SIZE, UnityInstance
from relay.protocol import (
    HEADER_SIZE,
    MAX_PAYLOAD_BYTES,
    PROTOCOL_VERSION,
    CommandMessage,
    CommandResultMessage,
    ErrorCode,
    ErrorMessage,
    InstancesMessage,
    InstanceStatus,
    MessageType,
    PingMessage,
    PongMessage,
    RegisteredMessage,
    RegisterMessage,
    RequestMessage,
    ResponseMessage,
    StatusMessage,
)
from relay.server import (
    _VALID_DETAILS,
    COMMAND_TIMEOUT_MS,
    DEFAULT_HOST,
    DEFAULT_PORT,
    HEARTBEAT_INTERVAL_MS,
    HEARTBEAT_MAX_RETRIES,
    HEARTBEAT_TIMEOUT_MS,
    LOG_BACKUP_COUNT,
    LOG_FORMAT,
    LOG_MAX_BYTES,
    RELOAD_GRACE_PERIOD_MS,
    RELOAD_TIMEOUT_MS,
)

# =============================================================================
# Protocol Constants
# =============================================================================


class TestProtocolConstantsCharacterization:
    """Freeze protocol constants to prevent accidental changes."""

    def test_protocol_version(self) -> None:
        assert PROTOCOL_VERSION == "1.0"

    def test_header_size(self) -> None:
        assert HEADER_SIZE == 4

    def test_max_payload_bytes(self) -> None:
        assert MAX_PAYLOAD_BYTES == 16 * 1024 * 1024  # 16 MiB


# =============================================================================
# Message Types
# =============================================================================


class TestMessageTypesCharacterization:
    """Freeze all MessageType enum values."""

    EXPECTED_MESSAGE_TYPES = {
        # Unity -> Relay
        "REGISTER": "REGISTER",
        "REGISTERED": "REGISTERED",
        "STATUS": "STATUS",
        "COMMAND_RESULT": "COMMAND_RESULT",
        "PONG": "PONG",
        # Relay -> Unity
        "PING": "PING",
        "COMMAND": "COMMAND",
        # CLI -> Relay
        "REQUEST": "REQUEST",
        "LIST_INSTANCES": "LIST_INSTANCES",
        "SET_DEFAULT": "SET_DEFAULT",
        # Relay -> CLI
        "RESPONSE": "RESPONSE",
        "ERROR": "ERROR",
        "INSTANCES": "INSTANCES",
    }

    def test_all_message_types_present(self) -> None:
        """All expected message types exist."""
        actual = {mt.name: mt.value for mt in MessageType}
        assert actual == self.EXPECTED_MESSAGE_TYPES

    def test_message_type_count(self) -> None:
        """Total number of message types is frozen."""
        assert len(MessageType) == 13


# =============================================================================
# Error Codes
# =============================================================================


class TestErrorCodesCharacterization:
    """Freeze all ErrorCode enum values."""

    EXPECTED_ERROR_CODES = {
        "INSTANCE_NOT_FOUND": "INSTANCE_NOT_FOUND",
        "INSTANCE_RELOADING": "INSTANCE_RELOADING",
        "INSTANCE_BUSY": "INSTANCE_BUSY",
        "INSTANCE_DISCONNECTED": "INSTANCE_DISCONNECTED",
        "COMMAND_NOT_FOUND": "COMMAND_NOT_FOUND",
        "INVALID_PARAMS": "INVALID_PARAMS",
        "TIMEOUT": "TIMEOUT",
        "INTERNAL_ERROR": "INTERNAL_ERROR",
        "PROTOCOL_ERROR": "PROTOCOL_ERROR",
        "MALFORMED_JSON": "MALFORMED_JSON",
        "PAYLOAD_TOO_LARGE": "PAYLOAD_TOO_LARGE",
        "PROTOCOL_VERSION_MISMATCH": "PROTOCOL_VERSION_MISMATCH",
        "CAPABILITY_NOT_SUPPORTED": "CAPABILITY_NOT_SUPPORTED",
        "QUEUE_FULL": "QUEUE_FULL",
        "STALE_REF": "STALE_REF",
        "AMBIGUOUS_INSTANCE": "AMBIGUOUS_INSTANCE",
    }

    def test_all_error_codes_present(self) -> None:
        """All expected error codes exist."""
        actual = {ec.name: ec.value for ec in ErrorCode}
        assert actual == self.EXPECTED_ERROR_CODES

    def test_error_code_count(self) -> None:
        """Total number of error codes is frozen."""
        assert len(ErrorCode) == 16


# =============================================================================
# Instance Status
# =============================================================================


class TestInstanceStatusCharacterization:
    """Freeze all InstanceStatus enum values."""

    EXPECTED_STATUSES = {
        "READY": "ready",
        "BUSY": "busy",
        "RELOADING": "reloading",
        "DISCONNECTED": "disconnected",
    }

    def test_all_statuses_present(self) -> None:
        """All expected status values exist."""
        actual = {s.name: s.value for s in InstanceStatus}
        assert actual == self.EXPECTED_STATUSES

    def test_status_count(self) -> None:
        """Total number of statuses is frozen."""
        assert len(InstanceStatus) == 4

    @pytest.mark.parametrize(
        ("status", "value"),
        [
            (InstanceStatus.READY, "ready"),
            (InstanceStatus.BUSY, "busy"),
            (InstanceStatus.RELOADING, "reloading"),
            (InstanceStatus.DISCONNECTED, "disconnected"),
        ],
    )
    def test_status_string_values(self, status: InstanceStatus, value: str) -> None:
        """Status string values match expected lowercase format."""
        assert status.value == value


# =============================================================================
# Heartbeat Constants
# =============================================================================


class TestHeartbeatConstantsCharacterization:
    """Freeze heartbeat timing constants."""

    def test_heartbeat_interval(self) -> None:
        assert HEARTBEAT_INTERVAL_MS == 5000

    def test_heartbeat_timeout(self) -> None:
        assert HEARTBEAT_TIMEOUT_MS == 15000

    def test_heartbeat_max_retries(self) -> None:
        assert HEARTBEAT_MAX_RETRIES == 3

    def test_reload_timeout(self) -> None:
        assert RELOAD_TIMEOUT_MS == 30000

    def test_reload_timeout_exceeds_heartbeat_timeout(self) -> None:
        """RELOAD_TIMEOUT must be >= HEARTBEAT_TIMEOUT for extended tolerance."""
        assert RELOAD_TIMEOUT_MS >= HEARTBEAT_TIMEOUT_MS


# =============================================================================
# Server Configuration Constants
# =============================================================================


class TestServerConfigCharacterization:
    """Freeze server configuration constants."""

    def test_default_host(self) -> None:
        assert DEFAULT_HOST == "127.0.0.1"

    def test_default_port(self) -> None:
        assert DEFAULT_PORT == 6500

    def test_command_timeout(self) -> None:
        assert COMMAND_TIMEOUT_MS == 30000

    def test_reload_grace_period(self) -> None:
        assert RELOAD_GRACE_PERIOD_MS == 60000


# =============================================================================
# Queue Constants
# =============================================================================


class TestQueueConstantsCharacterization:
    """Freeze command queue configuration."""

    def test_queue_max_size(self) -> None:
        assert QUEUE_MAX_SIZE == 10

    def test_queue_disabled_by_default(self) -> None:
        assert QUEUE_ENABLED is False


# =============================================================================
# Logging Constants
# =============================================================================


class TestLoggingConstantsCharacterization:
    """Freeze logging configuration."""

    def test_log_format(self) -> None:
        assert LOG_FORMAT == "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    def test_log_max_bytes(self) -> None:
        assert LOG_MAX_BYTES == 10 * 1024 * 1024  # 10 MB

    def test_log_backup_count(self) -> None:
        assert LOG_BACKUP_COUNT == 5


# =============================================================================
# Valid Status Details
# =============================================================================


class TestValidDetailsCharacterization:
    """Freeze allowed status detail values."""

    EXPECTED_DETAILS = frozenset(
        {
            "compiling",
            "running_tests",
            "asset_import",
            "playmode_transition",
            "editor_blocked",
        }
    )

    def test_all_valid_details(self) -> None:
        assert _VALID_DETAILS == self.EXPECTED_DETAILS

    def test_valid_details_count(self) -> None:
        assert len(_VALID_DETAILS) == 5


# =============================================================================
# Message Serialization Shape
# =============================================================================


class TestMessageSerializationCharacterization:
    """Freeze message serialization structure."""

    def test_register_message_keys(self) -> None:
        """RegisterMessage produces expected keys."""
        msg = RegisterMessage(
            instance_id="/test",
            project_name="Test",
            unity_version="2022.3",
            capabilities=["manage_editor"],
        )
        d = msg.to_dict()
        expected_keys = {
            "type",
            "ts",
            "protocol_version",
            "instance_id",
            "project_name",
            "unity_version",
            "capabilities",
            "bridge_version",
        }
        assert set(d.keys()) == expected_keys

    def test_registered_message_success_keys(self) -> None:
        """RegisteredMessage (success) produces expected keys."""
        msg = RegisteredMessage(success=True, heartbeat_interval_ms=5000)
        d = msg.to_dict()
        expected_keys = {"type", "ts", "success", "heartbeat_interval_ms"}
        assert set(d.keys()) == expected_keys

    def test_registered_message_error_keys(self) -> None:
        """RegisteredMessage (error) produces expected keys."""
        msg = RegisteredMessage(success=False, error={"code": "ERR", "message": "msg"})
        d = msg.to_dict()
        assert "error" in d
        assert "success" in d

    def test_ping_message_keys(self) -> None:
        """PingMessage produces expected keys."""
        msg = PingMessage()
        d = msg.to_dict()
        expected_keys = {"type", "ts"}
        assert set(d.keys()) == expected_keys

    def test_command_message_keys(self) -> None:
        """CommandMessage produces expected keys."""
        msg = CommandMessage(id="req-1", command="test", params={"key": "val"}, timeout_ms=30000)
        d = msg.to_dict()
        expected_keys = {"type", "ts", "id", "command", "params", "timeout_ms"}
        assert set(d.keys()) == expected_keys

    def test_response_message_keys(self) -> None:
        """ResponseMessage produces expected keys."""
        msg = ResponseMessage(id="req-1", success=True, data={"result": "ok"})
        d = msg.to_dict()
        # relay_version and bridge_version are empty strings, still serialized
        assert "type" in d
        assert "id" in d
        assert "success" in d
        assert "data" in d

    def test_error_message_from_code_structure(self) -> None:
        """ErrorMessage.from_code produces correct structure."""
        msg = ErrorMessage.from_code("req-1", ErrorCode.TIMEOUT, "Timed out")
        d = msg.to_dict()
        assert d["type"] == "ERROR"
        assert d["success"] is False
        assert d["error"]["code"] == "TIMEOUT"
        assert d["error"]["message"] == "Timed out"
        assert d["id"] == "req-1"

    def test_instances_message_keys(self) -> None:
        """InstancesMessage produces expected keys."""
        msg = InstancesMessage(id="req-list", success=True, data={"instances": []})
        d = msg.to_dict()
        expected_keys = {"type", "ts", "id", "success", "data"}
        assert set(d.keys()) == expected_keys


# =============================================================================
# UnityInstance.to_dict Shape
# =============================================================================


class TestInstanceDictCharacterization:
    """Freeze UnityInstance.to_dict() output shape."""

    def test_to_dict_keys_without_detail(self) -> None:
        """to_dict without status_detail produces expected keys."""
        instance = UnityInstance(
            instance_id="/test",
            project_name="Test",
            unity_version="2022.3",
            ref_id=1,
            capabilities=["manage_editor"],
            status=InstanceStatus.READY,
        )
        d = instance.to_dict(is_default=True)
        expected_keys = {
            "ref_id",
            "instance_id",
            "project_name",
            "unity_version",
            "bridge_version",
            "status",
            "is_default",
            "capabilities",
            "queue_size",
        }
        assert set(d.keys()) == expected_keys

    def test_to_dict_keys_with_detail(self) -> None:
        """to_dict with status_detail adds the key."""
        instance = UnityInstance(
            instance_id="/test",
            project_name="Test",
            unity_version="2022.3",
            ref_id=1,
            status=InstanceStatus.BUSY,
            status_detail="compiling",
        )
        d = instance.to_dict()
        assert "status_detail" in d
        assert d["status_detail"] == "compiling"


# =============================================================================
# ErrorMessage Default Values
# =============================================================================


class TestErrorMessageDefaults:
    """Freeze ErrorMessage default field values."""

    def test_default_success_is_false(self) -> None:
        msg = ErrorMessage()
        assert msg.success is False

    def test_default_type_is_error(self) -> None:
        msg = ErrorMessage()
        assert msg.type == "ERROR"


# =============================================================================
# Message Type Literal Values
# =============================================================================


class TestMessageTypeLiterals:
    """Verify each message class produces correct 'type' value."""

    @pytest.mark.parametrize(
        ("cls", "expected_type"),
        [
            (RegisterMessage, "REGISTER"),
            (RegisteredMessage, "REGISTERED"),
            (StatusMessage, "STATUS"),
            (CommandResultMessage, "COMMAND_RESULT"),
            (PongMessage, "PONG"),
            (PingMessage, "PING"),
            (CommandMessage, "COMMAND"),
            (ResponseMessage, "RESPONSE"),
            (ErrorMessage, "ERROR"),
            (InstancesMessage, "INSTANCES"),
        ],
    )
    def test_message_class_type_value(self, cls: type, expected_type: str) -> None:
        """Each message class serializes to the correct 'type' string."""
        # CommandMessage and RequestMessage require command to be non-empty
        if cls is CommandMessage or cls is RequestMessage:
            msg = cls(command="test")
        else:
            msg = cls()
        assert msg.to_dict()["type"] == expected_type
