"""Test API for Unity CLI."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from unity_cli.client import RelayConnection


class TestAPI:
    """Test execution operations."""

    def __init__(self, conn: RelayConnection) -> None:
        self._conn = conn

    def run(
        self,
        mode: str = "edit",
        *,
        test_names: list[str] | None = None,
        categories: list[str] | None = None,
        assemblies: list[str] | None = None,
        group_pattern: str | None = None,
    ) -> dict[str, Any]:
        """Run Unity tests with optional filtering.

        Args:
            mode: Test mode - "edit" or "play"
            test_names: Specific test names to run (e.g., "MyTests.TestMethod")
            categories: Test categories to run
            assemblies: Assembly names to run tests from
            group_pattern: Regex pattern for test names/namespaces

        Returns:
            Dictionary with test run results
        """
        params: dict[str, Any] = {"action": "run", "mode": mode}

        if test_names:
            params["testNames"] = test_names
        if categories:
            params["categories"] = categories
        if assemblies:
            params["assemblies"] = assemblies
        if group_pattern:
            params["groupPattern"] = group_pattern

        return self._conn.send_request("tests", params)

    def list(self, mode: str = "edit") -> dict[str, Any]:
        """List available tests.

        Args:
            mode: Test mode - "edit" or "play"

        Returns:
            Dictionary with available tests
        """
        return self._conn.send_request("tests", {"action": "list", "mode": mode})

    def status(self) -> dict[str, Any]:
        """Get status of running tests.

        Returns:
            Dictionary with test run status
        """
        return self._conn.send_request("tests", {"action": "status"})
