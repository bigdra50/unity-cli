#!/usr/bin/env python3
"""
Unity MCP Client Library
=========================

Complete Python client for Unity MCP TCP protocol.
Supports all 10 tools with 60+ actions.

Usage:
    from unity_mcp_client import UnityMCPClient

    client = UnityMCPClient()

    # Console operations
    logs = client.read_console(types=["error"], count=10)
    client.clear_console()

    # Editor control
    client.editor.play()
    state = client.editor.get_state()

    # GameObject operations
    obj = client.gameobject.create("Player", primitive_type="Cube")
    client.gameobject.modify("Player", position=[0, 5, 0])

    # Scene management
    client.scene.load(path="Assets/Scenes/MainScene.unity")

    # Asset operations
    client.asset.create("Assets/Materials/New.mat", "Material")

    # Run tests
    results = client.run_tests(mode="edit")
"""

import socket
import json
import struct
import subprocess
import sys
from typing import Dict, List, Optional, Any, Union


def detect_port() -> int:
    """
    Detect Unity MCP port from EditorPrefs (macOS only).

    Returns the port from Unity EditorPrefs if available,
    otherwise falls back to the default port 6400.
    """
    if sys.platform != 'darwin':
        return 6400

    try:
        result = subprocess.run(
            ["defaults", "read", "com.unity3d.UnityEditor5.x", "MCPForUnity.UnitySocketPort"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return int(result.stdout.strip())
    except (subprocess.TimeoutExpired, ValueError, FileNotFoundError):
        pass

    return 6400


class UnityMCPError(Exception):
    """Unity MCP operation error"""
    pass


class UnityMCPConnection:
    """Low-level Unity MCP connection handler"""

    def __init__(self, host='localhost', port=6400, timeout=5.0):
        self.host = host
        self.port = port
        self.timeout = timeout

    def _write_frame(self, sock, payload_bytes: bytes):
        """Write framed message: 8-byte big-endian length + payload"""
        length = len(payload_bytes)
        header = struct.pack('>Q', length)
        sock.sendall(header + payload_bytes)

    def _read_frame(self, sock) -> str:
        """Read framed message: 8-byte header + payload"""
        sock.settimeout(self.timeout)

        # Read 8-byte header
        header = sock.recv(8)
        if len(header) != 8:
            raise UnityMCPError(f"Expected 8-byte header, got {len(header)} bytes")

        # Parse length (big-endian)
        length = struct.unpack('>Q', header)[0]

        # Read payload
        payload = b""
        remaining = length
        while remaining > 0:
            chunk = sock.recv(min(remaining, 4096))
            if not chunk:
                raise UnityMCPError("Connection closed while reading payload")
            payload += chunk
            remaining -= len(chunk)

        return payload.decode('utf-8')

    def send_command(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send command and return response"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            try:
                sock.connect((self.host, self.port))
            except ConnectionRefusedError:
                raise UnityMCPError(
                    f"Cannot connect to Unity Editor at {self.host}:{self.port}.\n"
                    "Please ensure:\n"
                    "  1. Unity Editor is open\n"
                    "  2. MCP For Unity bridge is running (Window > MCP For Unity)"
                )

            # Read WELCOME
            welcome = sock.recv(1024).decode('utf-8')
            if 'WELCOME UNITY-MCP' not in welcome:
                raise UnityMCPError(f"Invalid handshake: {welcome}")

            # Build message
            message = {
                "type": tool_name,
                "params": params
            }

            # Send framed request
            payload = json.dumps(message).encode('utf-8')
            self._write_frame(sock, payload)

            # Read framed response
            response_text = self._read_frame(sock)
            response = json.loads(response_text)

            # Check status (support both old 'status' and new 'success' fields)
            if response.get("status") == "error":
                raise UnityMCPError(f"{tool_name} failed: {response.get('error', 'Unknown error')}")

            if response.get("success") is False:
                raise UnityMCPError(f"{tool_name} failed: {response.get('message', 'Unknown error')}")

            return response.get("result", response)

        finally:
            sock.close()

    def read_resource(self, resource_name: str, params: Dict[str, Any] = {}) -> Dict[str, Any]:
        """Read resource and return response (uses same protocol as Tools)"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            try:
                sock.connect((self.host, self.port))
            except ConnectionRefusedError:
                raise UnityMCPError(
                    f"Cannot connect to Unity Editor at {self.host}:{self.port}.\n"
                    "Please ensure:\n"
                    "  1. Unity Editor is open\n"
                    "  2. MCP For Unity bridge is running (Window > MCP For Unity)"
                )

            # Read WELCOME
            welcome = sock.recv(1024).decode('utf-8')
            if 'WELCOME UNITY-MCP' not in welcome:
                raise UnityMCPError(f"Invalid handshake: {welcome}")

            # Build message - Resources use same format as Tools
            message = {
                "type": resource_name,
                "params": params
            }

            # Send framed request
            payload = json.dumps(message).encode('utf-8')
            self._write_frame(sock, payload)

            # Read framed response
            response_text = self._read_frame(sock)
            response = json.loads(response_text)

            # Check status (support both old 'status' and new 'success' fields)
            if response.get("status") == "error":
                raise UnityMCPError(f"Resource {resource_name} failed: {response.get('error', 'Unknown error')}")

            if response.get("success") is False:
                raise UnityMCPError(f"Resource {resource_name} failed: {response.get('message', 'Unknown error')}")

            return response.get("result", response)

        finally:
            sock.close()


class ConsoleAPI:
    """Console log operations"""

    def __init__(self, conn: UnityMCPConnection):
        self._conn = conn

    def get(self, types: Optional[List[str]] = None, count: int = 100,
            format: str = "detailed", include_stacktrace: bool = True,
            filter_text: Optional[str] = None) -> Dict[str, Any]:
        """Get console logs"""
        params = {
            "action": "get",
            "format": format,
            "include_stacktrace": include_stacktrace
        }
        if types:
            params["types"] = types
        if count:
            params["count"] = count
        if filter_text:
            params["filter_text"] = filter_text

        return self._conn.send_command("read_console", params)

    def clear(self) -> Dict[str, Any]:
        """Clear console"""
        return self._conn.send_command("read_console", {"action": "clear"})


class EditorAPI:
    """Editor control operations"""

    def __init__(self, conn: UnityMCPConnection):
        self._conn = conn

    def play(self) -> Dict[str, Any]:
        """Enter play mode"""
        return self._conn.send_command("manage_editor", {"action": "play"})

    def pause(self) -> Dict[str, Any]:
        """Pause/unpause game"""
        return self._conn.send_command("manage_editor", {"action": "pause"})

    def stop(self) -> Dict[str, Any]:
        """Exit play mode"""
        return self._conn.send_command("manage_editor", {"action": "stop"})

    def get_state(self) -> Dict[str, Any]:
        """Get editor state via Resource API"""
        return self._conn.read_resource("get_editor_state")

    def get_project_root(self) -> str:
        """Get project root path via Resource API"""
        result = self._conn.read_resource("get_project_info")
        data = result.get("data", {})
        return data.get("projectRoot", "")

    def add_tag(self, tag_name: str) -> Dict[str, Any]:
        """Add tag"""
        return self._conn.send_command("manage_editor", {"action": "add_tag", "tagName": tag_name})

    def remove_tag(self, tag_name: str) -> Dict[str, Any]:
        """Remove tag"""
        return self._conn.send_command("manage_editor", {"action": "remove_tag", "tagName": tag_name})

    def get_tags(self) -> Dict[str, Any]:
        """Get all tags via Resource API"""
        return self._conn.read_resource("get_tags")

    def get_layers(self) -> Dict[str, Any]:
        """Get all layers via Resource API"""
        return self._conn.read_resource("get_layers")


class GameObjectAPI:
    """GameObject operations"""

    def __init__(self, conn: UnityMCPConnection):
        self._conn = conn

    def create(self, name: str, parent: Optional[str] = None,
               position: Optional[List[float]] = None,
               rotation: Optional[List[float]] = None,
               scale: Optional[List[float]] = None,
               primitive_type: Optional[str] = None,
               prefab_path: Optional[str] = None,
               **kwargs) -> Dict[str, Any]:
        """Create GameObject"""
        params = {"action": "create", "name": name}
        if parent:
            params["parent"] = parent
        if position:
            params["position"] = position
        if rotation:
            params["rotation"] = rotation
        if scale:
            params["scale"] = scale
        if primitive_type:
            params["primitiveType"] = primitive_type
        if prefab_path:
            params["prefabPath"] = prefab_path
        params.update(kwargs)

        return self._conn.send_command("manage_gameobject", params)

    def modify(self, target: str, search_method: str = "by_name",
               name: Optional[str] = None,
               position: Optional[List[float]] = None,
               rotation: Optional[List[float]] = None,
               scale: Optional[List[float]] = None,
               component_properties: Optional[Dict[str, Dict]] = None,
               **kwargs) -> Dict[str, Any]:
        """Modify GameObject"""
        params = {"action": "modify", "target": target, "searchMethod": search_method}
        if name:
            params["name"] = name
        if position:
            params["position"] = position
        if rotation:
            params["rotation"] = rotation
        if scale:
            params["scale"] = scale
        if component_properties:
            params["componentProperties"] = component_properties
        params.update(kwargs)

        return self._conn.send_command("manage_gameobject", params)

    def delete(self, target: str, search_method: str = "by_name") -> Dict[str, Any]:
        """Delete GameObject"""
        return self._conn.send_command("manage_gameobject", {
            "action": "delete",
            "target": target,
            "searchMethod": search_method
        })

    def find(self, search_method: str = "by_name", search_term: Optional[str] = None,
             target: Optional[str] = None, find_all: bool = False,
             search_inactive: bool = False) -> Dict[str, Any]:
        """Find GameObject(s)"""
        params = {"action": "find", "searchMethod": search_method, "findAll": find_all}
        if search_term:
            params["searchTerm"] = search_term
        if target:
            params["target"] = target
        if search_inactive:
            params["searchInactive"] = search_inactive

        return self._conn.send_command("manage_gameobject", params)

    def add_component(self, target: str, components: List[str],
                      search_method: str = "by_name",
                      component_properties: Optional[Dict[str, Dict]] = None) -> Dict[str, Any]:
        """Add component(s)"""
        params = {
            "action": "add_component",
            "target": target,
            "componentsToAdd": components,
            "searchMethod": search_method
        }
        if component_properties:
            params["componentProperties"] = component_properties

        return self._conn.send_command("manage_gameobject", params)

    def remove_component(self, target: str, components: List[str],
                         search_method: str = "by_name") -> Dict[str, Any]:
        """Remove component(s)"""
        return self._conn.send_command("manage_gameobject", {
            "action": "remove_component",
            "target": target,
            "componentsToRemove": components,
            "searchMethod": search_method
        })


class SceneAPI:
    """Scene management operations"""

    def __init__(self, conn: UnityMCPConnection):
        self._conn = conn

    def create(self, name: str, path: str = "Scenes") -> Dict[str, Any]:
        """Create new scene"""
        return self._conn.send_command("manage_scene", {
            "action": "create",
            "name": name,
            "path": path
        })

    def load(self, name: Optional[str] = None, path: Optional[str] = None,
             build_index: Optional[int] = None) -> Dict[str, Any]:
        """Load scene"""
        params = {"action": "load"}
        if name:
            params["name"] = name
        if path:
            params["path"] = path
        if build_index is not None:
            params["buildIndex"] = build_index

        return self._conn.send_command("manage_scene", params)

    def save(self, name: Optional[str] = None, path: Optional[str] = None) -> Dict[str, Any]:
        """Save current scene"""
        params = {"action": "save"}
        if name:
            params["name"] = name
        if path:
            params["path"] = path

        return self._conn.send_command("manage_scene", params)

    def get_hierarchy(self) -> Dict[str, Any]:
        """Get scene hierarchy"""
        return self._conn.send_command("manage_scene", {"action": "get_hierarchy"})

    def get_active(self) -> Dict[str, Any]:
        """Get active scene info"""
        return self._conn.send_command("manage_scene", {"action": "get_active"})


class AssetAPI:
    """Asset management operations"""

    def __init__(self, conn: UnityMCPConnection):
        self._conn = conn

    def create(self, path: str, asset_type: str, properties: Optional[Dict] = None) -> Dict[str, Any]:
        """Create asset"""
        params = {"action": "create", "path": path, "assetType": asset_type}
        if properties:
            params["properties"] = properties

        return self._conn.send_command("manage_asset", params)

    def modify(self, path: str, properties: Dict) -> Dict[str, Any]:
        """Modify asset"""
        return self._conn.send_command("manage_asset", {
            "action": "modify",
            "path": path,
            "properties": properties
        })

    def delete(self, path: str) -> Dict[str, Any]:
        """Delete asset"""
        return self._conn.send_command("manage_asset", {"action": "delete", "path": path})

    def search(self, search_pattern: Optional[str] = None,
               filter_type: Optional[str] = None,
               path: Optional[str] = None,
               page_size: int = 50) -> Dict[str, Any]:
        """Search assets"""
        params = {"action": "search", "pageSize": page_size}
        if search_pattern:
            params["searchPattern"] = search_pattern
        if filter_type:
            params["filterType"] = filter_type
        if path:
            params["path"] = path

        return self._conn.send_command("manage_asset", params)


class UnityMCPClient:
    """
    Complete Unity MCP client with all tools

    Usage:
        client = UnityMCPClient()

        # Direct console access
        logs = client.read_console(types=["error"])
        client.clear_console()

        # Via API objects
        client.editor.play()
        client.gameobject.create("Player", primitive_type="Cube")
        client.scene.load(path="Assets/Scenes/Main.unity")
    """

    def __init__(self, host='localhost', port=6400, timeout=5.0):
        self._conn = UnityMCPConnection(host, port, timeout)

        # API objects
        self.console = ConsoleAPI(self._conn)
        self.editor = EditorAPI(self._conn)
        self.gameobject = GameObjectAPI(self._conn)
        self.scene = SceneAPI(self._conn)
        self.asset = AssetAPI(self._conn)

    # Convenience methods
    def read_console(self, **kwargs) -> Dict[str, Any]:
        """Get console logs (convenience method)"""
        return self.console.get(**kwargs)

    def clear_console(self) -> Dict[str, Any]:
        """Clear console (convenience method)"""
        return self.console.clear()

    def execute_menu_item(self, menu_path: str) -> Dict[str, Any]:
        """Execute Unity menu item"""
        return self._conn.send_command("execute_menu_item", {"menu_path": menu_path})

    def run_tests(self, mode: str = "edit", timeout_seconds: int = 600) -> Dict[str, Any]:
        """Run Unity tests"""
        return self._conn.send_command("run_tests", {
            "mode": mode,
            "timeoutSeconds": timeout_seconds
        })

    def manage_script(self, action: str, name: str, path: str = "Scripts", **kwargs) -> Dict[str, Any]:
        """Manage C# scripts"""
        params = {"action": action, "name": name, "path": path}
        params.update(kwargs)
        return self._conn.send_command("manage_script", params)

    def manage_shader(self, action: str, name: str, path: str = "Shaders", **kwargs) -> Dict[str, Any]:
        """Manage shaders"""
        params = {"action": action, "name": name, "path": path}
        params.update(kwargs)
        return self._conn.send_command("manage_shader", params)

    def manage_prefabs(self, action: str, **kwargs) -> Dict[str, Any]:
        """Manage prefabs"""
        params = {"action": action}
        params.update(kwargs)
        return self._conn.send_command("manage_prefabs", params)


def main():
    """CLI entry point for unity-mcp command"""
    import sys
    import argparse

    parser = argparse.ArgumentParser(
        description="Unity MCP Client CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available commands:
  console                 Get console logs
  clear                   Clear console
  play                    Enter play mode
  stop                    Exit play mode
  state                   Get editor state
  refresh                 Refresh assets
  find <name>             Find GameObject by name
  tests <mode>            Run tests (edit|play)
  verify                  Verify build (refresh → clear → compile wait → console)

Examples:
  %(prog)s state
  %(prog)s refresh
  %(prog)s console --types error --count 50
  %(prog)s verify --timeout 120 --retry 5
  %(prog)s verify --types error warning log
  %(prog)s find "Main Camera"
  %(prog)s tests edit
        """
    )
    parser.add_argument("command", help="Command to execute (see available commands below)")
    parser.add_argument("args", nargs="*", help="Command arguments")
    parser.add_argument("--port", type=int, default=None,
                        help="Server port (auto-detected on macOS if not specified)")
    parser.add_argument("--host", default="localhost", help="Server host")
    parser.add_argument("--count", type=int, default=20, help="Number of console logs to retrieve (default: 20)")
    parser.add_argument("--types", nargs="+", default=["error", "warning"],
                        help="Log types to retrieve (default: error warning). Options: error, warning, log")
    parser.add_argument("--timeout", type=int, default=60,
                        help="Maximum wait time for compilation in seconds (default: 60, verify only)")
    parser.add_argument("--retry", type=int, default=3,
                        help="Maximum connection retry attempts (default: 3, verify only)")

    args = parser.parse_args()

    # Auto-detect port if not specified
    port = args.port if args.port is not None else detect_port()
    client = UnityMCPClient(host=args.host, port=port)

    try:
        if args.command == "console":
            result = client.read_console(types=args.types, count=args.count)
            print(json.dumps(result, indent=2, ensure_ascii=False))

        elif args.command == "clear":
            result = client.clear_console()
            print("Console cleared")

        elif args.command == "play":
            client.editor.play()
            print("Entered play mode")

        elif args.command == "stop":
            client.editor.stop()
            print("Exited play mode")

        elif args.command == "state":
            result = client.editor.get_state()
            print(json.dumps(result, indent=2, ensure_ascii=False))

        elif args.command == "refresh":
            print("Refreshing assets...")
            client.execute_menu_item("Assets/Refresh")
            print("✓ Asset refresh triggered")

        elif args.command == "find" and args.args:
            result = client.gameobject.find(search_method="by_name", search_term=args.args[0])
            print(json.dumps(result, indent=2, ensure_ascii=False))

        elif args.command == "tests":
            mode = args.args[0] if args.args else "edit"
            result = client.run_tests(mode=mode)
            print(json.dumps(result, indent=2, ensure_ascii=False))

        elif args.command == "verify":
            import time

            # Step 1: Refresh assets
            print("=== Refreshing Assets ===")
            client.execute_menu_item("Assets/Refresh")
            print("✓ Asset refresh triggered")

            # Step 2: Clear console (to capture only new errors)
            print("\n=== Clearing Console ===")
            client.clear_console()
            print("✓ Console cleared")

            # Step 3: Wait for compilation using isCompiling state
            print("\n=== Waiting for Compilation ===")
            poll_interval = 1.0
            elapsed = 0.0
            connection_failures = 0

            while elapsed < args.timeout:
                time.sleep(poll_interval)
                elapsed += poll_interval

                try:
                    state = client.editor.get_state()
                    is_compiling = state.get('data', {}).get('isCompiling', False)

                    if not is_compiling:
                        print(f"\n✓ Compilation complete ({elapsed:.1f}s)")
                        break

                    print(f"  Compiling... ({elapsed:.1f}s)", end='\r')
                    connection_failures = 0  # Reset on successful connection

                except UnityMCPError as e:
                    connection_failures += 1
                    if connection_failures <= args.retry:
                        print(f"  Connection lost, retrying ({connection_failures}/{args.retry})...", end='\r')
                        continue
                    print(f"\n⚠ Connection failed after {args.retry} retries")
                    sys.exit(1)
            else:
                print(f"\n⚠ Timeout after {args.timeout}s")
                sys.exit(1)

            # Step 4: Check console logs
            print("\n=== Console Logs ===")
            logs = client.read_console(types=args.types, count=args.count)

            if logs['data']:
                print(f"Found {len(logs['data'])} log entries (types: {', '.join(args.types)}, max: {args.count}):\n")
                for log in logs['data']:
                    print(f"[{log['type']}] {log['message']}")
                    if log.get('file'):
                        print(f"  at {log['file']}:{log.get('line', '?')}")
            else:
                print(f"✓ No logs found (searched types: {', '.join(args.types)})")

        else:
            print(f"Unknown command: {args.command}")
            print("Available: console, clear, play, stop, state, refresh, find, tests, verify")
            sys.exit(1)

    except UnityMCPError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


# CLI Interface
if __name__ == "__main__":
    main()
