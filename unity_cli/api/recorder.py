"""Recorder API for Unity CLI."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from unity_cli.client import RelayConnection


class RecorderAPI:
    """Frame recording operations."""

    def __init__(self, conn: RelayConnection) -> None:
        self._conn = conn

    def start(
        self,
        fps: int = 30,
        format: Literal["png", "jpg"] = "jpg",
        quality: int = 75,
        width: int = 1920,
        height: int = 1080,
        camera: str | None = None,
        output_dir: str | None = None,
    ) -> dict[str, Any]:
        """Start recording frames.

        Args:
            fps: Target frames per second (default: 30, max: 120)
            format: Image format - "png" or "jpg" (default: jpg)
            quality: JPEG quality 1-100 (default: 75)
            width: Image width (default: 1920)
            height: Image height (default: 1080)
            camera: Camera GameObject name. Uses Main Camera if not specified.
            output_dir: Output directory. Auto-generated if not specified.

        Returns:
            Dictionary with recording start info.
        """
        params: dict[str, Any] = {
            "action": "start",
            "fps": fps,
            "format": format,
            "quality": quality,
            "width": width,
            "height": height,
        }
        if camera is not None:
            params["camera"] = camera
        if output_dir is not None:
            params["outputDir"] = output_dir
        return self._conn.send_request("recorder", params)

    def stop(self) -> dict[str, Any]:
        """Stop recording and get results.

        Returns:
            Dictionary with recording results including:
            - frameCount: Number of frames captured
            - elapsed: Recording duration in seconds
            - fps: Achieved frames per second
            - outputDir: Output directory path
            - format: Image format used
        """
        return self._conn.send_request("recorder", {"action": "stop"})

    def status(self) -> dict[str, Any]:
        """Get current recording status.

        Returns:
            Dictionary with recording status including:
            - recording: Whether recording is active
            - frameCount: Frames captured so far
            - elapsed: Time elapsed in seconds
            - fps: Current frames per second
            - pendingWrites: Number of frames waiting to be written to disk
        """
        return self._conn.send_request("recorder", {"action": "status"})
