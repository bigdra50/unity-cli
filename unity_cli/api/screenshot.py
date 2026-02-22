"""Screenshot API for Unity CLI."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from unity_cli.client import RelayConnection


class ScreenshotAPI:
    """Screenshot capture operations."""

    def __init__(self, conn: RelayConnection) -> None:
        self._conn = conn

    def capture(
        self,
        source: Literal["game", "scene", "camera"] = "game",
        path: str | None = None,
        super_size: int = 1,
        width: int | None = None,
        height: int | None = None,
        camera: str | None = None,
        format: Literal["png", "jpg"] | None = None,
        quality: int | None = None,
    ) -> dict[str, Any]:
        """Capture a screenshot from GameView, SceneView, or Camera.

        Args:
            source: "game" for GameView (async, requires editor focus),
                    "scene" for SceneView,
                    "camera" for Camera.Render (sync, focus-independent)
            path: Output file path. If not specified, saves to Screenshots/ with timestamp
            super_size: Resolution multiplier for GameView (1-4). Ignored for scene/camera.
            width: Image width for camera source (default: 1920)
            height: Image height for camera source (default: 1080)
            camera: Camera GameObject name for camera source. Uses Main Camera if not specified.
            format: Image format - "png" or "jpg" (default: png)
            quality: JPEG quality 1-100 (default: 75). Only used with jpg format.

        Returns:
            Dictionary with capture result including:
            - message: Status message
            - path: Output file path
            - source: Capture source ("game", "scene", or "camera")
            - format: Image format used
            - width/height: Image dimensions (for scene/camera captures)
            - camera: Camera name (for camera captures)
        """
        params: dict[str, Any] = {
            "action": "capture",
            "source": source,
            "superSize": super_size,
        }
        if path is not None:
            params["path"] = path
        if width is not None:
            params["width"] = width
        if height is not None:
            params["height"] = height
        if camera is not None:
            params["camera"] = camera
        if format is not None:
            params["format"] = format
        if quality is not None:
            params["quality"] = quality
        return self._conn.send_request("screenshot", params)

    def burst(
        self,
        count: int = 10,
        interval_ms: int = 0,
        format: Literal["png", "jpg"] = "jpg",
        quality: int = 75,
        width: int = 1920,
        height: int = 1080,
        camera: str | None = None,
        output_dir: str | None = None,
    ) -> dict[str, Any]:
        """Capture multiple frames in rapid succession.

        Args:
            count: Number of frames to capture (default: 10, max: 1000)
            interval_ms: Minimum interval between frames in ms (0 = fastest possible)
            format: Image format - "png" or "jpg" (default: jpg)
            quality: JPEG quality 1-100 (default: 75)
            width: Image width (default: 1920)
            height: Image height (default: 1080)
            camera: Camera GameObject name. Uses Main Camera if not specified.
            output_dir: Output directory. Auto-generated if not specified.

        Returns:
            Dictionary with burst result including:
            - frameCount: Number of frames captured
            - outputDir: Output directory path
            - format: Image format used
            - elapsed: Total time in seconds
            - fps: Achieved frames per second
            - paths: List of frame file paths
        """
        params: dict[str, Any] = {
            "action": "burst",
            "count": count,
            "interval_ms": interval_ms,
            "format": format,
            "quality": quality,
            "width": width,
            "height": height,
        }
        if camera is not None:
            params["camera"] = camera
        if output_dir is not None:
            params["outputDir"] = output_dir
        return self._conn.send_request("screenshot", params, timeout_ms=120000)
