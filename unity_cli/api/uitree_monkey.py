"""Monkey testing — random UI element interaction with error monitoring."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from unity_cli.api.console import ConsoleAPI
    from unity_cli.api.uitree import UITreeAPI


@dataclass
class MonkeyResult:
    """Result of a monkey test run."""

    total_actions: int = 0
    errors: list[dict[str, Any]] = field(default_factory=list)
    actions: list[dict[str, Any]] = field(default_factory=list)
    seed: int = 0
    duration_ms: int = 0


def _should_stop(action_count: int, count: int | None, start: float, duration: float | None) -> bool:
    """Check if the monkey loop should terminate."""
    if count is not None and action_count >= count:
        return True
    if duration is not None and (time.time() - start) >= duration:
        return True
    return False


class MonkeyRunner:
    """Run random UI interactions and monitor for errors."""

    def __init__(self, uitree: UITreeAPI, console: ConsoleAPI) -> None:
        self._uitree = uitree
        self._console = console

    def run(
        self,
        panel: str,
        duration: float | None = None,
        count: int | None = None,
        seed: int | None = None,
        type_filter: str | None = None,
        class_filter: str | None = None,
        stop_on_error: bool = False,
        interval: float = 0.2,
        error_check_interval: int = 5,
    ) -> MonkeyResult:
        """Run monkey test.

        Args:
            panel: Target panel name.
            duration: Max duration in seconds.
            count: Max number of actions.
            seed: Random seed for reproducibility.
            type_filter: Filter elements by type.
            class_filter: Filter elements by USS class.
            stop_on_error: Stop on first console error.
            interval: Delay between actions in seconds.
            error_check_interval: Check console errors every N actions.

        Returns:
            MonkeyResult with actions performed and errors found.
        """
        if duration is None and count is None:
            count = 100

        actual_seed = seed if seed is not None else random.randint(0, 2**31)
        rng = random.Random(actual_seed)

        self._console.clear()
        start = time.time()
        result = MonkeyResult(seed=actual_seed)

        action_count = 0
        while not _should_stop(action_count, count, start, duration):
            elements = self._query_elements(panel, type_filter, class_filter)
            if not elements:
                break

            action_count += 1
            self._perform_action(rng, elements, result)

            if action_count % error_check_interval == 0:
                if self._handle_errors(result, stop_on_error):
                    break

            time.sleep(interval)

        # Final error check
        self._handle_errors(result, stop_on_error=False)

        result.total_actions = action_count
        result.duration_ms = int((time.time() - start) * 1000)
        return result

    def _perform_action(self, rng: random.Random, elements: list[dict[str, Any]], result: MonkeyResult) -> None:
        """Pick a random element and click it."""
        target = rng.choice(elements)
        try:
            self._uitree.click(ref=target["ref"])
        except Exception as e:
            result.errors.append({"message": str(e), "ref": target["ref"]})
            return
        result.actions.append(
            {
                "ref": target["ref"],
                "name": target.get("name", ""),
                "type": target.get("type", ""),
            }
        )

    def _handle_errors(self, result: MonkeyResult, stop_on_error: bool) -> bool:
        """Check for errors and return True if should stop."""
        errors = self._check_errors()
        if errors:
            result.errors.extend(errors)
            return stop_on_error
        return False

    def _query_elements(self, panel: str, type_filter: str | None, class_filter: str | None) -> list[dict[str, Any]]:
        """Query interactive elements from the panel."""
        resp = self._uitree.query(
            panel=panel,
            type=type_filter,
            class_name=class_filter,
        )
        elements: list[dict[str, Any]] = resp.get("matches", [])
        return elements

    def _check_errors(self) -> list[dict[str, Any]]:
        """Check console for new errors."""
        resp = self._console.get(types=["error"])
        entries: list[dict[str, Any]] = resp.get("entries", [])
        if entries:
            self._console.clear()
        return entries
