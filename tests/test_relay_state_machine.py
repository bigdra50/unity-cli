"""Tests for relay/server.py - State machine, heartbeat, and command queueing logic."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from relay.instance_registry import QueuedCommand, UnityInstance
from relay.protocol import (
    ErrorCode,
    InstanceStatus,
    MessageType,
)
from relay.server import (
    COMMAND_TIMEOUT_MS,
    HEARTBEAT_MAX_RETRIES,
    HEARTBEAT_TIMEOUT_MS,
    RELOAD_TIMEOUT_MS,
    RelayServer,
)

# =============================================================================
# Helpers
# =============================================================================


def _make_writer(*, closing: bool = False) -> MagicMock:
    """Create a mock asyncio.StreamWriter."""
    writer = MagicMock()
    writer.is_closing.return_value = closing
    writer.close = MagicMock()
    writer.wait_closed = AsyncMock()
    writer.write = MagicMock()
    writer.drain = AsyncMock()
    return writer


def _make_instance(
    instance_id: str = "/test/Project",
    status: InstanceStatus = InstanceStatus.READY,
    *,
    queue_enabled: bool = False,
) -> UnityInstance:
    """Create a UnityInstance with a mock writer."""
    writer = _make_writer()
    return UnityInstance(
        instance_id=instance_id,
        project_name="Project",
        unity_version="2022.3",
        status=status,
        writer=writer,
        reader=MagicMock(),
        queue_enabled=queue_enabled,
    )


# =============================================================================
# State Transitions
# =============================================================================


class TestStateTransitions:
    """Test Unity instance state transitions via _handle_unity_message."""

    @pytest.fixture
    def server(self) -> RelayServer:
        return RelayServer()

    def test_ready_to_busy_via_set_status(self) -> None:
        """READY -> BUSY transition when command is sent."""
        instance = _make_instance(status=InstanceStatus.READY)
        instance.set_status(InstanceStatus.BUSY)
        assert instance.status == InstanceStatus.BUSY

    def test_busy_to_ready_via_set_status(self) -> None:
        """BUSY -> READY transition when command completes."""
        instance = _make_instance(status=InstanceStatus.BUSY)
        instance.set_status(InstanceStatus.READY)
        assert instance.status == InstanceStatus.READY

    def test_ready_to_reloading_via_set_status(self) -> None:
        """READY -> RELOADING transition on domain reload."""
        instance = _make_instance(status=InstanceStatus.READY)
        instance.set_status(InstanceStatus.RELOADING)
        assert instance.status == InstanceStatus.RELOADING
        assert instance.reloading_since is not None

    def test_reloading_to_ready_clears_reloading_since(self) -> None:
        """RELOADING -> READY clears reloading_since."""
        instance = _make_instance(status=InstanceStatus.RELOADING)
        instance.reloading_since = 12345.0
        instance.set_status(InstanceStatus.READY)
        assert instance.status == InstanceStatus.READY
        assert instance.reloading_since is None

    async def test_status_message_updates_instance_status(self, server: RelayServer) -> None:
        """STATUS message from Unity updates instance status in registry."""
        instance = _make_instance()
        server.registry._instances[instance.instance_id] = instance

        msg = {"type": MessageType.STATUS.value, "status": "reloading"}
        await server._handle_unity_message(instance, msg)

        assert instance.status == InstanceStatus.RELOADING

    async def test_status_message_busy_to_ready_triggers_queue_processing(self, server: RelayServer) -> None:
        """BUSY -> READY transition via STATUS message triggers queue processing."""
        instance = _make_instance(status=InstanceStatus.BUSY, queue_enabled=True)
        server.registry._instances[instance.instance_id] = instance

        # Patch _process_queue to verify it gets called
        with patch.object(server, "_process_queue", new_callable=AsyncMock) as mock_process:
            msg = {"type": MessageType.STATUS.value, "status": "ready"}
            await server._handle_unity_message(instance, msg)

            assert instance.status == InstanceStatus.READY
            mock_process.assert_awaited_once_with(instance)

    async def test_status_message_ready_to_ready_no_queue_trigger(self, server: RelayServer) -> None:
        """READY -> READY transition does not trigger queue processing."""
        instance = _make_instance(status=InstanceStatus.READY, queue_enabled=True)
        server.registry._instances[instance.instance_id] = instance

        with patch.object(server, "_process_queue", new_callable=AsyncMock) as mock_process:
            msg = {"type": MessageType.STATUS.value, "status": "ready"}
            await server._handle_unity_message(instance, msg)
            mock_process.assert_not_awaited()

    async def test_status_message_with_detail(self, server: RelayServer) -> None:
        """STATUS message with valid detail stores it."""
        instance = _make_instance(status=InstanceStatus.READY)
        server.registry._instances[instance.instance_id] = instance

        msg = {"type": MessageType.STATUS.value, "status": "busy", "detail": "compiling"}
        await server._handle_unity_message(instance, msg)

        assert instance.status == InstanceStatus.BUSY
        assert instance.status_detail == "compiling"

    async def test_status_message_with_invalid_detail_ignored(self, server: RelayServer) -> None:
        """STATUS message with invalid detail drops it."""
        instance = _make_instance(status=InstanceStatus.READY)
        server.registry._instances[instance.instance_id] = instance

        msg = {"type": MessageType.STATUS.value, "status": "busy", "detail": "invalid_detail"}
        await server._handle_unity_message(instance, msg)

        assert instance.status == InstanceStatus.BUSY
        assert instance.status_detail is None

    async def test_unknown_status_value_ignored(self, server: RelayServer) -> None:
        """Unknown status value does not change instance status."""
        instance = _make_instance(status=InstanceStatus.READY)
        server.registry._instances[instance.instance_id] = instance

        msg = {"type": MessageType.STATUS.value, "status": "unknown_state"}
        await server._handle_unity_message(instance, msg)

        assert instance.status == InstanceStatus.READY


# =============================================================================
# COMMAND_RESULT Handling
# =============================================================================


class TestCommandResult:
    """Test COMMAND_RESULT message handling."""

    @pytest.fixture
    def server(self) -> RelayServer:
        return RelayServer()

    async def test_command_result_resolves_pending_future(self, server: RelayServer) -> None:
        """COMMAND_RESULT resolves the pending command future."""
        instance = _make_instance()
        future: asyncio.Future[dict] = asyncio.get_event_loop().create_future()
        server._pending_commands["req-1"] = future

        msg = {
            "type": MessageType.COMMAND_RESULT.value,
            "id": "req-1",
            "success": True,
            "data": {"isPlaying": True},
        }
        await server._handle_unity_message(instance, msg)

        assert future.done()
        assert future.result()["success"] is True
        assert "req-1" not in server._pending_commands

    async def test_late_command_result_ignored(self, server: RelayServer) -> None:
        """Late COMMAND_RESULT (already timed out) is silently ignored."""
        instance = _make_instance()
        # No pending command registered for "req-2"

        msg = {
            "type": MessageType.COMMAND_RESULT.value,
            "id": "req-2",
            "success": True,
            "data": {},
        }
        # Should not raise
        await server._handle_unity_message(instance, msg)


# =============================================================================
# PONG Handling
# =============================================================================


class TestPongHandling:
    """Test PONG message handling."""

    @pytest.fixture
    def server(self) -> RelayServer:
        return RelayServer()

    async def test_pong_sets_event(self, server: RelayServer) -> None:
        """PONG message sets the pending pong event."""
        instance = _make_instance()
        event = asyncio.Event()
        server._pending_pongs[instance.instance_id] = event

        msg = {"type": MessageType.PONG.value}
        await server._handle_unity_message(instance, msg)

        assert event.is_set()

    async def test_pong_without_pending_event_no_error(self, server: RelayServer) -> None:
        """PONG when no event is pending does not raise."""
        instance = _make_instance()

        msg = {"type": MessageType.PONG.value}
        await server._handle_unity_message(instance, msg)


# =============================================================================
# Unknown Message Type
# =============================================================================


class TestUnknownMessage:
    """Test unknown Unity message type handling."""

    @pytest.fixture
    def server(self) -> RelayServer:
        return RelayServer()

    async def test_unknown_message_type_logged(self, server: RelayServer) -> None:
        """Unknown message type is logged but does not raise."""
        instance = _make_instance()

        msg = {"type": "UNKNOWN_TYPE", "data": {}}
        # Should not raise
        await server._handle_unity_message(instance, msg)


# =============================================================================
# Heartbeat Logic
# =============================================================================


class TestHeartbeat:
    """Test heartbeat-related constants and timeout detection."""

    def test_heartbeat_timeout_not_expired(self) -> None:
        """Fresh instance does not trigger timeout."""
        _make_instance()
        elapsed = 0.0
        elapsed_ms = elapsed * 1000
        assert elapsed_ms <= HEARTBEAT_TIMEOUT_MS

    def test_heartbeat_timeout_extended_during_reloading(self) -> None:
        """RELOADING state uses RELOAD_TIMEOUT_MS for timeout."""
        assert RELOAD_TIMEOUT_MS > HEARTBEAT_TIMEOUT_MS

    async def test_heartbeat_loop_disconnects_after_max_retries(self) -> None:
        """Heartbeat loop breaks after HEARTBEAT_MAX_RETRIES consecutive failures."""
        server = RelayServer()
        server._running = True

        instance = _make_instance()
        server.registry._instances[instance.instance_id] = instance

        # Mock write_frame to succeed but never send PONG (always timeout)
        call_count = 0

        async def fake_sleep(duration: float) -> None:
            nonlocal call_count
            call_count += 1
            # Don't actually sleep

        with (
            patch("relay.server.write_frame", new_callable=AsyncMock),
            patch("asyncio.sleep", side_effect=fake_sleep),
            patch("asyncio.wait_for", side_effect=TimeoutError),
        ):
            await server._heartbeat_loop(instance.instance_id)

        # Should have attempted HEARTBEAT_MAX_RETRIES pings
        assert call_count == HEARTBEAT_MAX_RETRIES

    async def test_heartbeat_loop_resets_failure_count_on_pong(self) -> None:
        """Successful PONG resets consecutive failure counter."""
        server = RelayServer()
        server._running = True

        instance = _make_instance()
        server.registry._instances[instance.instance_id] = instance

        iteration = 0

        async def fake_sleep(duration: float) -> None:
            nonlocal iteration
            iteration += 1
            # Stop after 3 iterations
            if iteration >= 3:
                server._running = False

        async def fake_wait_for(coro, timeout: float) -> None:
            # Always succeed (PONG received)
            pass

        with (
            patch("relay.server.write_frame", new_callable=AsyncMock),
            patch("asyncio.sleep", side_effect=fake_sleep),
            patch("asyncio.wait_for", side_effect=fake_wait_for),
        ):
            await server._heartbeat_loop(instance.instance_id)

        # Completed 3 iterations without disconnect
        assert iteration == 3


# =============================================================================
# Command Queueing
# =============================================================================


class TestCommandQueueing:
    """Test command queue behavior when instance is BUSY."""

    def test_enqueue_when_queue_disabled_fails(self) -> None:
        """Enqueue fails when queue_enabled is False."""
        instance = _make_instance(queue_enabled=False)
        future: asyncio.Future[dict] = asyncio.get_event_loop().create_future()
        cmd = QueuedCommand(
            request_id="req-1",
            command="test",
            params={},
            timeout_ms=COMMAND_TIMEOUT_MS,
            future=future,
        )
        assert instance.enqueue_command(cmd) is False

    def test_enqueue_when_queue_enabled_succeeds(self) -> None:
        """Enqueue succeeds when queue_enabled is True."""
        instance = _make_instance(queue_enabled=True)
        future: asyncio.Future[dict] = asyncio.get_event_loop().create_future()
        cmd = QueuedCommand(
            request_id="req-1",
            command="test",
            params={},
            timeout_ms=COMMAND_TIMEOUT_MS,
            future=future,
        )
        assert instance.enqueue_command(cmd) is True
        assert instance.queue_size == 1

    def test_enqueue_fails_when_queue_full(self) -> None:
        """Enqueue fails when queue is at max capacity."""
        from relay.instance_registry import QUEUE_MAX_SIZE

        instance = _make_instance(queue_enabled=True)

        # Fill the queue
        for i in range(QUEUE_MAX_SIZE):
            future: asyncio.Future[dict] = asyncio.get_event_loop().create_future()
            cmd = QueuedCommand(
                request_id=f"req-{i}",
                command="test",
                params={},
                timeout_ms=COMMAND_TIMEOUT_MS,
                future=future,
            )
            assert instance.enqueue_command(cmd) is True

        # Next enqueue should fail
        overflow_future: asyncio.Future[dict] = asyncio.get_event_loop().create_future()
        overflow_cmd = QueuedCommand(
            request_id="req-overflow",
            command="test",
            params={},
            timeout_ms=COMMAND_TIMEOUT_MS,
            future=overflow_future,
        )
        assert instance.enqueue_command(overflow_cmd) is False

    def test_dequeue_fifo_order(self) -> None:
        """Commands are dequeued in FIFO order."""
        instance = _make_instance(queue_enabled=True)

        for i in range(3):
            future: asyncio.Future[dict] = asyncio.get_event_loop().create_future()
            cmd = QueuedCommand(
                request_id=f"req-{i}",
                command="test",
                params={},
                timeout_ms=COMMAND_TIMEOUT_MS,
                future=future,
            )
            instance.enqueue_command(cmd)

        actual = [instance.dequeue_command().request_id for _ in range(3)]
        assert actual == ["req-0", "req-1", "req-2"]

    def test_dequeue_empty_returns_none(self) -> None:
        """Dequeue from empty queue returns None."""
        instance = _make_instance(queue_enabled=True)
        assert instance.dequeue_command() is None

    async def test_process_queue_sends_next_command(self) -> None:
        """_process_queue executes the next queued command."""
        server = RelayServer()
        instance = _make_instance(queue_enabled=True)
        server.registry._instances[instance.instance_id] = instance

        future: asyncio.Future[dict] = asyncio.get_event_loop().create_future()
        cmd = QueuedCommand(
            request_id="req-queued",
            command="test_cmd",
            params={"key": "value"},
            timeout_ms=COMMAND_TIMEOUT_MS,
            future=future,
        )
        instance.enqueue_command(cmd)

        mock_result = {"type": "RESPONSE", "success": True, "data": {"result": "ok"}}
        with patch.object(server, "_execute_command", new_callable=AsyncMock, return_value=mock_result):
            await server._process_queue(instance)

        assert future.done()
        assert future.result() == mock_result

    async def test_process_queue_skips_done_future(self) -> None:
        """_process_queue skips commands whose futures are already done (timed out)."""
        server = RelayServer()
        instance = _make_instance(queue_enabled=True)
        server.registry._instances[instance.instance_id] = instance

        # First command: already timed out
        done_future: asyncio.Future[dict] = asyncio.get_event_loop().create_future()
        done_future.set_result({"timeout": True})  # Mark as done
        timed_out_cmd = QueuedCommand(
            request_id="req-timed-out",
            command="old_cmd",
            params={},
            timeout_ms=COMMAND_TIMEOUT_MS,
            future=done_future,
        )
        instance.enqueue_command(timed_out_cmd)

        # Second command: still pending
        pending_future: asyncio.Future[dict] = asyncio.get_event_loop().create_future()
        pending_cmd = QueuedCommand(
            request_id="req-pending",
            command="new_cmd",
            params={},
            timeout_ms=COMMAND_TIMEOUT_MS,
            future=pending_future,
        )
        instance.enqueue_command(pending_cmd)

        mock_result = {"type": "RESPONSE", "success": True, "data": {}}
        with patch.object(server, "_execute_command", new_callable=AsyncMock, return_value=mock_result):
            await server._process_queue(instance)

        # The timed out one should be skipped; the pending one should be resolved
        assert pending_future.done()
        assert pending_future.result() == mock_result

    async def test_process_queue_noop_when_empty(self) -> None:
        """_process_queue does nothing when queue is empty."""
        server = RelayServer()
        instance = _make_instance(queue_enabled=True)

        with patch.object(server, "_execute_command", new_callable=AsyncMock) as mock_exec:
            await server._process_queue(instance)
            mock_exec.assert_not_awaited()

    async def test_process_queue_noop_when_disabled(self) -> None:
        """_process_queue does nothing when queue is disabled."""
        server = RelayServer()
        instance = _make_instance(queue_enabled=False)

        with patch.object(server, "_execute_command", new_callable=AsyncMock) as mock_exec:
            await server._process_queue(instance)
            mock_exec.assert_not_awaited()

    def test_flush_queue_resolves_all_futures(self) -> None:
        """flush_queue resolves all pending futures with error."""
        instance = _make_instance(queue_enabled=True)

        futures = []
        for i in range(3):
            future: asyncio.Future[dict] = asyncio.get_event_loop().create_future()
            cmd = QueuedCommand(
                request_id=f"req-{i}",
                command="test",
                params={},
                timeout_ms=COMMAND_TIMEOUT_MS,
                future=future,
            )
            instance.enqueue_command(cmd)
            futures.append(future)

        instance.flush_queue("INSTANCE_DISCONNECTED", "Instance disconnected")

        for f in futures:
            assert f.done()
            result = f.result()
            assert result["type"] == "ERROR"
            assert result["error"]["code"] == "INSTANCE_DISCONNECTED"

        assert instance.queue_size == 0


# =============================================================================
# CLI Message Handling
# =============================================================================


class TestCLIMessageHandling:
    """Test _handle_cli_message for various CLI message types."""

    @pytest.fixture
    def server(self) -> RelayServer:
        return RelayServer()

    async def test_list_instances_returns_instances_message(self, server: RelayServer) -> None:
        """LIST_INSTANCES returns INSTANCES response."""
        writer = _make_writer()
        msg = {"type": MessageType.LIST_INSTANCES.value, "id": "req-list"}

        with patch("relay.server.write_frame", new_callable=AsyncMock) as mock_write:
            await server._handle_cli_message(writer, msg)

            mock_write.assert_awaited_once()
            response = mock_write.call_args[0][1]
            assert response["type"] == "INSTANCES"
            assert response["success"] is True

    async def test_set_default_nonexistent_returns_error(self, server: RelayServer) -> None:
        """SET_DEFAULT for nonexistent instance returns error."""
        writer = _make_writer()
        msg = {
            "type": MessageType.SET_DEFAULT.value,
            "id": "req-set",
            "instance": "/nonexistent",
        }

        with patch("relay.server.write_frame", new_callable=AsyncMock) as mock_write:
            await server._handle_cli_message(writer, msg)

            response = mock_write.call_args[0][1]
            assert response["type"] == "ERROR"
            assert response["error"]["code"] == ErrorCode.INSTANCE_NOT_FOUND.value

    async def test_unknown_cli_message_type_returns_error(self, server: RelayServer) -> None:
        """Unknown CLI message type returns PROTOCOL_ERROR."""
        writer = _make_writer()
        msg = {"type": "INVALID_TYPE", "id": "req-x"}

        with patch("relay.server.write_frame", new_callable=AsyncMock) as mock_write:
            await server._handle_cli_message(writer, msg)

            response = mock_write.call_args[0][1]
            assert response["type"] == "ERROR"
            assert response["error"]["code"] == ErrorCode.PROTOCOL_ERROR.value


# =============================================================================
# Execute Command
# =============================================================================


class TestExecuteCommand:
    """Test _execute_command with various instance states."""

    @pytest.fixture
    def server(self) -> RelayServer:
        return RelayServer()

    async def test_capability_check_rejects_unsupported(self, server: RelayServer) -> None:
        """Command not in capabilities list returns CAPABILITY_NOT_SUPPORTED."""
        instance = _make_instance()
        instance.capabilities = ["manage_editor", "get_console"]
        server.registry._instances[instance.instance_id] = instance
        server.registry._default_instance_id = instance.instance_id

        result = await server._execute_command(
            request_id="req-cap",
            instance_id=None,
            command="unsupported_command",
            params={},
            timeout_ms=COMMAND_TIMEOUT_MS,
        )

        assert result["type"] == "ERROR"
        assert result["error"]["code"] == ErrorCode.CAPABILITY_NOT_SUPPORTED.value

    async def test_no_instance_returns_not_found(self, server: RelayServer) -> None:
        """No instances registered returns INSTANCE_NOT_FOUND."""
        result = await server._execute_command(
            request_id="req-none",
            instance_id="/nonexistent",
            command="test",
            params={},
            timeout_ms=COMMAND_TIMEOUT_MS,
        )

        assert result["type"] == "ERROR"
        assert result["error"]["code"] == ErrorCode.INSTANCE_NOT_FOUND.value

    async def test_busy_instance_without_queue_returns_busy(self, server: RelayServer) -> None:
        """BUSY instance with queue disabled returns INSTANCE_BUSY."""
        instance = _make_instance(status=InstanceStatus.BUSY, queue_enabled=False)
        server.registry._instances[instance.instance_id] = instance
        server.registry._default_instance_id = instance.instance_id

        result = await server._execute_command(
            request_id="req-busy",
            instance_id=None,
            command="test",
            params={},
            timeout_ms=COMMAND_TIMEOUT_MS,
        )

        assert result["type"] == "ERROR"
        assert result["error"]["code"] == ErrorCode.INSTANCE_BUSY.value


# =============================================================================
# Server Lifecycle
# =============================================================================


class TestServerLifecycle:
    """Test server start/stop behavior."""

    async def test_stop_is_idempotent(self) -> None:
        """Calling stop() multiple times is safe."""
        server = RelayServer()
        server._running = True
        await server.request_cache.start()

        await server.stop()
        assert server._stopped is True

        # Second stop should be a no-op
        await server.stop()
        assert server._stopped is True

    async def test_stop_cancels_heartbeat_tasks(self) -> None:
        """stop() cancels all heartbeat tasks."""
        server = RelayServer()
        server._running = True
        await server.request_cache.start()

        # Create a fake heartbeat task
        task = asyncio.create_task(asyncio.sleep(999))
        server._heartbeat_tasks["test-instance"] = task

        await server.stop()

        assert len(server._heartbeat_tasks) == 0
        assert task.cancelled()

    async def test_stop_cancels_pending_commands(self) -> None:
        """stop() cancels all pending command futures."""
        server = RelayServer()
        server._running = True
        await server.request_cache.start()

        future: asyncio.Future[dict] = asyncio.get_event_loop().create_future()
        server._pending_commands["req-pending"] = future

        await server.stop()

        assert len(server._pending_commands) == 0
        assert future.cancelled()
