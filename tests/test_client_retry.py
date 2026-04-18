"""Tests for unity_cli/client.py - Retry logic, backoff calculation, and error classification."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from unity_cli.client import RelayConnection
from unity_cli.exceptions import (
    InstanceError,
    ProtocolError,
    TimeoutError,
    UnityCLIError,
)

# =============================================================================
# Retryable Error Classification
# =============================================================================


class TestRetryableErrors:
    """Test _RETRYABLE_CODES classification."""

    @pytest.mark.parametrize(
        "code",
        ["INSTANCE_RELOADING", "INSTANCE_BUSY", "TIMEOUT", "INSTANCE_DISCONNECTED"],
    )
    def test_retryable_codes(self, code: str) -> None:
        """These error codes are retryable."""
        assert code in RelayConnection._RETRYABLE_CODES

    @pytest.mark.parametrize(
        "code",
        [
            "INSTANCE_NOT_FOUND",
            "AMBIGUOUS_INSTANCE",
            "COMMAND_NOT_FOUND",
            "INVALID_PARAMS",
            "INTERNAL_ERROR",
            "PROTOCOL_ERROR",
            "MALFORMED_JSON",
            "PAYLOAD_TOO_LARGE",
            "PROTOCOL_VERSION_MISMATCH",
            "CAPABILITY_NOT_SUPPORTED",
            "QUEUE_FULL",
            "STALE_REF",
        ],
    )
    def test_non_retryable_codes(self, code: str) -> None:
        """These error codes are not retryable."""
        assert code not in RelayConnection._RETRYABLE_CODES


class TestInstanceErrorCodes:
    """Test _INSTANCE_ERROR_CODES classification."""

    @pytest.mark.parametrize(
        "code",
        [
            "INSTANCE_NOT_FOUND",
            "AMBIGUOUS_INSTANCE",
            "INSTANCE_RELOADING",
            "INSTANCE_BUSY",
            "INSTANCE_DISCONNECTED",
        ],
    )
    def test_instance_error_codes(self, code: str) -> None:
        """These codes are classified as instance errors."""
        assert code in RelayConnection._INSTANCE_ERROR_CODES


# =============================================================================
# Exponential Backoff
# =============================================================================


class TestExponentialBackoff:
    """Test _maybe_retry backoff calculation."""

    @pytest.fixture
    def conn(self) -> RelayConnection:
        return RelayConnection(
            retry_initial_ms=500,
            retry_max_ms=8000,
            retry_max_time_ms=45000,
        )

    @pytest.mark.parametrize(
        ("attempt", "expected_backoff"),
        [
            (0, 500),  # 500 * 2^0 = 500
            (1, 1000),  # 500 * 2^1 = 1000
            (2, 2000),  # 500 * 2^2 = 2000
            (3, 4000),  # 500 * 2^3 = 4000
            (4, 8000),  # 500 * 2^4 = 16000 -> capped at 8000
            (5, 8000),  # 500 * 2^5 = 32000 -> capped at 8000
        ],
    )
    def test_backoff_doubles_with_cap(self, conn: RelayConnection, attempt: int, expected_backoff: int) -> None:
        """Backoff doubles each attempt, capped at retry_max_ms."""
        error = InstanceError("Instance busy", "INSTANCE_BUSY")
        sleep_ms = None

        def capture_sleep(duration: float) -> None:
            nonlocal sleep_ms
            sleep_ms = int(duration * 1000)

        with patch("time.sleep", side_effect=capture_sleep):
            conn._maybe_retry(
                error=error,
                command="test",
                elapsed_ms=0,
                retry_initial_ms=500,
                retry_max_ms=8000,
                retry_max_time_ms=45000,
                attempt=attempt,
            )

        assert sleep_ms == expected_backoff

    def test_non_retryable_error_raises_immediately(self, conn: RelayConnection) -> None:
        """Non-retryable error is re-raised without sleeping."""
        error = InstanceError("Not found", "INSTANCE_NOT_FOUND")

        with pytest.raises(InstanceError):
            conn._maybe_retry(
                error=error,
                command="test",
                elapsed_ms=0,
                retry_initial_ms=500,
                retry_max_ms=8000,
                retry_max_time_ms=45000,
                attempt=0,
            )

    def test_max_time_exceeded_raises_timeout(self, conn: RelayConnection) -> None:
        """Raises TimeoutError when next backoff would exceed max time."""
        error = InstanceError("Busy", "INSTANCE_BUSY")

        with pytest.raises(TimeoutError, match="Max retry time would be exceeded"):
            conn._maybe_retry(
                error=error,
                command="test",
                elapsed_ms=44600,  # 44.6s elapsed
                retry_initial_ms=500,
                retry_max_ms=8000,
                retry_max_time_ms=45000,
                attempt=0,  # next backoff = 500ms, total = 45100ms > 45000ms
            )


# =============================================================================
# on_retry Callback
# =============================================================================


class TestOnRetryCallback:
    """Test on_retry callback invocation."""

    def test_on_retry_called_with_correct_args(self) -> None:
        """on_retry receives (code, message, attempt, backoff_ms)."""
        callback = MagicMock()
        conn = RelayConnection(on_retry=callback)

        error = InstanceError("Reloading", "INSTANCE_RELOADING")

        with patch("time.sleep"):
            conn._maybe_retry(
                error=error,
                command="test",
                elapsed_ms=0,
                retry_initial_ms=500,
                retry_max_ms=8000,
                retry_max_time_ms=45000,
                attempt=0,
            )

        callback.assert_called_once_with("INSTANCE_RELOADING", "Reloading", 1, 500)

    def test_on_retry_attempt_increments(self) -> None:
        """on_retry attempt number increments (1-indexed)."""
        callback = MagicMock()
        conn = RelayConnection(on_retry=callback)

        error = InstanceError("Busy", "INSTANCE_BUSY")

        with patch("time.sleep"):
            conn._maybe_retry(
                error=error,
                command="test",
                elapsed_ms=0,
                retry_initial_ms=500,
                retry_max_ms=8000,
                retry_max_time_ms=45000,
                attempt=2,
            )

        callback.assert_called_once_with("INSTANCE_BUSY", "Busy", 3, 2000)

    def test_on_retry_not_called_when_none(self) -> None:
        """No callback invocation when on_retry is None."""
        conn = RelayConnection(on_retry=None)
        error = InstanceError("Busy", "INSTANCE_BUSY")

        # Should not raise AttributeError
        with patch("time.sleep"):
            conn._maybe_retry(
                error=error,
                command="test",
                elapsed_ms=0,
                retry_initial_ms=500,
                retry_max_ms=8000,
                retry_max_time_ms=45000,
                attempt=0,
            )


# =============================================================================
# send_request Retry Loop
# =============================================================================


class TestSendRequestRetry:
    """Test send_request retry behavior end-to-end."""

    def test_success_on_first_attempt(self) -> None:
        """Successful first attempt returns immediately."""
        conn = RelayConnection()
        expected = {"isPlaying": True}

        with patch.object(conn, "_send_request_once", return_value=expected):
            actual = conn.send_request("test", {})

        assert actual == expected

    def test_retry_on_instance_busy_then_success(self) -> None:
        """Retries on INSTANCE_BUSY, then succeeds."""
        conn = RelayConnection(retry_initial_ms=1, retry_max_time_ms=5000)
        expected = {"isPlaying": True}

        call_count = 0

        def fake_send_once(*args, **kwargs) -> dict:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise InstanceError("Busy", "INSTANCE_BUSY")
            return expected

        with (
            patch.object(conn, "_send_request_once", side_effect=fake_send_once),
            patch("time.sleep"),
        ):
            actual = conn.send_request("test", {})

        assert actual == expected
        assert call_count == 2

    def test_retry_on_instance_reloading_then_success(self) -> None:
        """Retries on INSTANCE_RELOADING, then succeeds."""
        conn = RelayConnection(retry_initial_ms=1, retry_max_time_ms=5000)
        expected = {"state": "ready"}

        call_count = 0

        def fake_send_once(*args, **kwargs) -> dict:
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise InstanceError("Reloading", "INSTANCE_RELOADING")
            return expected

        with (
            patch.object(conn, "_send_request_once", side_effect=fake_send_once),
            patch("time.sleep"),
        ):
            actual = conn.send_request("test", {})

        assert actual == expected
        assert call_count == 3

    def test_no_retry_on_instance_not_found(self) -> None:
        """INSTANCE_NOT_FOUND is not retried."""
        conn = RelayConnection()

        with (
            patch.object(
                conn,
                "_send_request_once",
                side_effect=InstanceError("Not found", "INSTANCE_NOT_FOUND"),
            ),
            pytest.raises(InstanceError) as exc_info,
        ):
            conn.send_request("test", {})

        assert exc_info.value.code == "INSTANCE_NOT_FOUND"

    def test_no_retry_on_ambiguous_instance(self) -> None:
        """AMBIGUOUS_INSTANCE is not retried."""
        conn = RelayConnection()

        with (
            patch.object(
                conn,
                "_send_request_once",
                side_effect=InstanceError("Ambiguous", "AMBIGUOUS_INSTANCE"),
            ),
            pytest.raises(InstanceError) as exc_info,
        ):
            conn.send_request("test", {})

        assert exc_info.value.code == "AMBIGUOUS_INSTANCE"

    def test_max_retry_time_exceeded(self) -> None:
        """Raises TimeoutError when max retry time is exceeded."""
        conn = RelayConnection(retry_initial_ms=1, retry_max_time_ms=10)

        def fake_send_once(*args, **kwargs) -> None:
            # Simulate slow responses
            time.sleep(0.02)
            raise InstanceError("Busy", "INSTANCE_BUSY")

        with (
            patch.object(conn, "_send_request_once", side_effect=fake_send_once),
            pytest.raises(TimeoutError, match="Max retry time"),
        ):
            conn.send_request("test", {})

    def test_retry_on_timeout_error(self) -> None:
        """Retries on TIMEOUT error code."""
        conn = RelayConnection(retry_initial_ms=1, retry_max_time_ms=5000)
        expected = {"done": True}

        call_count = 0

        def fake_send_once(*args, **kwargs) -> dict:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise TimeoutError("Timed out", "TIMEOUT")
            return expected

        with (
            patch.object(conn, "_send_request_once", side_effect=fake_send_once),
            patch("time.sleep"),
        ):
            actual = conn.send_request("test", {})

        assert actual == expected
        assert call_count == 2


# =============================================================================
# _handle_response Error Classification
# =============================================================================


class TestHandleResponse:
    """Test _handle_response error classification."""

    @pytest.fixture
    def conn(self) -> RelayConnection:
        return RelayConnection()

    def test_error_response_instance_error(self, conn: RelayConnection) -> None:
        """ERROR with instance code raises InstanceError."""
        response = {
            "type": "ERROR",
            "error": {"code": "INSTANCE_NOT_FOUND", "message": "Not found"},
        }

        with pytest.raises(InstanceError) as exc_info:
            conn._handle_response(response, "test")

        assert exc_info.value.code == "INSTANCE_NOT_FOUND"

    def test_error_response_timeout(self, conn: RelayConnection) -> None:
        """ERROR with TIMEOUT code raises TimeoutError."""
        response = {
            "type": "ERROR",
            "error": {"code": "TIMEOUT", "message": "Timed out"},
        }

        with pytest.raises(TimeoutError) as exc_info:
            conn._handle_response(response, "test")

        assert exc_info.value.code == "TIMEOUT"

    def test_error_response_unknown_code(self, conn: RelayConnection) -> None:
        """ERROR with unknown code raises UnityCLIError."""
        response = {
            "type": "ERROR",
            "error": {"code": "SOME_NEW_ERROR", "message": "New error"},
        }

        with pytest.raises(UnityCLIError) as exc_info:
            conn._handle_response(response, "test")

        assert exc_info.value.code == "SOME_NEW_ERROR"

    def test_success_response_returns_data(self, conn: RelayConnection) -> None:
        """Successful RESPONSE returns data dict."""
        response = {
            "type": "RESPONSE",
            "success": True,
            "data": {"isPlaying": True},
        }

        actual = conn._handle_response(response, "test")
        assert actual == {"isPlaying": True}

    def test_failed_response_raises(self, conn: RelayConnection) -> None:
        """RESPONSE with success=False raises UnityCLIError."""
        response = {
            "type": "RESPONSE",
            "success": False,
            "error": {"code": "COMMAND_FAILED", "message": "Failed"},
        }

        with pytest.raises(UnityCLIError) as exc_info:
            conn._handle_response(response, "test")

        assert exc_info.value.code == "COMMAND_FAILED"

    def test_unexpected_response_type_raises_protocol_error(self, conn: RelayConnection) -> None:
        """Unexpected message type raises ProtocolError."""
        response = {"type": "UNKNOWN", "data": {}}

        with pytest.raises(ProtocolError):
            conn._handle_response(response, "test")

    def test_instances_response_returns_data(self, conn: RelayConnection) -> None:
        """INSTANCES response returns data dict."""
        response = {
            "type": "INSTANCES",
            "data": {"instances": [{"instance_id": "/test", "status": "ready"}]},
        }

        actual = conn._handle_response(response, "test")
        assert "instances" in actual


# =============================================================================
# Version Info Callback
# =============================================================================


class TestVersionInfoCallback:
    """Test on_version_info callback behavior."""

    def test_version_info_called_once(self) -> None:
        """on_version_info is called only once on first success."""
        callback = MagicMock()
        conn = RelayConnection(on_version_info=callback)

        response = {
            "type": "RESPONSE",
            "success": True,
            "data": {},
            "relay_version": "1.0.0",
            "bridge_version": "2.0.0",
        }

        conn._handle_response(response, "test")
        conn._handle_response(response, "test")

        callback.assert_called_once_with("1.0.0", "2.0.0")

    def test_version_info_not_called_without_versions(self) -> None:
        """on_version_info not called when versions are empty."""
        callback = MagicMock()
        conn = RelayConnection(on_version_info=callback)

        response = {
            "type": "RESPONSE",
            "success": True,
            "data": {},
        }

        conn._handle_response(response, "test")

        callback.assert_not_called()


# =============================================================================
# Connection Defaults
# =============================================================================


class TestConnectionDefaults:
    """Test RelayConnection default values."""

    def test_default_host_and_port(self) -> None:
        """Default host and port match config constants."""
        conn = RelayConnection()
        assert conn.host == "127.0.0.1"
        assert conn.port == 6500

    def test_default_retry_params(self) -> None:
        """Default retry parameters match documented values."""
        conn = RelayConnection()
        assert conn.retry_initial_ms == 500
        assert conn.retry_max_ms == 8000
        assert conn.retry_max_time_ms == 30000

    def test_custom_retry_params(self) -> None:
        """Custom retry parameters are stored correctly."""
        conn = RelayConnection(
            retry_initial_ms=1000,
            retry_max_ms=16000,
            retry_max_time_ms=60000,
        )
        assert conn.retry_initial_ms == 1000
        assert conn.retry_max_ms == 16000
        assert conn.retry_max_time_ms == 60000

    def test_client_id_generated(self) -> None:
        """Client ID is auto-generated."""
        conn = RelayConnection()
        assert len(conn._client_id) == 12

    def test_instance_parameter(self) -> None:
        """Instance parameter is stored."""
        conn = RelayConnection(instance="/path/to/project")
        assert conn.instance == "/path/to/project"
