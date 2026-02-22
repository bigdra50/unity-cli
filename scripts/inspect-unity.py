#!/usr/bin/env python3
"""Run static analysis on Unity C# code.

Uses JetBrains inspectcode (ReSharper CLI) and similarity-csharp to detect
code issues and duplicates in TestProject/.

Usage:
    python scripts/inspect-unity.py                       # run both tools
    python scripts/inspect-unity.py --only inspect        # inspectcode only
    python scripts/inspect-unity.py --only similarity     # similarity only
    python scripts/inspect-unity.py --severity SUGGESTION # lower threshold
    python scripts/inspect-unity.py --threshold 0.9       # stricter similarity
    python scripts/inspect-unity.py --output-dir ./reports
    python scripts/inspect-unity.py --keep-sln
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEST_PROJECT = ROOT / "TestProject"

EXCLUDED_INSPECTIONS = frozenset({"InconsistentNaming"})


# ── tool checks ──────────────────────────────────────────────────────────


def check_tool(name: str) -> bool:
    return shutil.which(name) is not None


def ensure_tools(run_inspect: bool, run_similarity: bool) -> bool:
    missing: list[str] = []
    if not check_tool("dotnet"):
        missing.append("dotnet")
    if run_inspect and not check_tool("jb"):
        missing.append("jb (dotnet tool install -g JetBrains.ReSharper.GlobalTools)")
    if run_similarity and not check_tool("similarity-csharp"):
        missing.append("similarity-csharp (dotnet tool install -g SimilarityCSharp.Cli)")

    if missing:
        print("Missing required tools:")
        for m in missing:
            print(f"  - {m}")
        return False
    return True


# ── .sln generation ─────────────────────────────────────────────────────


def find_csproj_files() -> list[Path]:
    return sorted(TEST_PROJECT.glob("*.csproj"))


def sln_exists() -> bool:
    return any(TEST_PROJECT.glob("*.sln"))


def generate_sln() -> Path:
    sln_path = TEST_PROJECT / "TestProject.sln"
    subprocess.run(
        ["dotnet", "new", "sln", "--name", "TestProject", "--output", str(TEST_PROJECT)],
        check=True,
        capture_output=True,
    )
    for csproj in find_csproj_files():
        subprocess.run(
            ["dotnet", "sln", str(sln_path), "add", str(csproj)],
            check=True,
            capture_output=True,
        )
    print(f"Generated {sln_path.relative_to(ROOT)}")
    return sln_path


# ── inspectcode ──────────────────────────────────────────────────────────


def run_inspectcode(sln_path: Path, output_dir: Path, severity: str) -> tuple[Path, int]:
    """Run jb inspectcode and return (filtered SARIF path, issue count)."""
    raw_sarif = output_dir / "inspectcode-raw.sarif"
    filtered_sarif = output_dir / "inspectcode.sarif"

    sln_files = list(TEST_PROJECT.glob("*.sln"))
    target = sln_files[0] if sln_files else sln_path

    cmd = [
        "jb",
        "inspectcode",
        str(target),
        "--no-build",
        "--format=Sarif",
        f"--severity={severity}",
        f"--output={raw_sarif}",
    ]
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"inspectcode failed (exit {result.returncode}):")
        if result.stderr:
            print(result.stderr)
        return filtered_sarif, 0

    if not raw_sarif.exists():
        print("inspectcode produced no output")
        return filtered_sarif, 0

    sarif = json.loads(raw_sarif.read_text())
    total_removed = 0
    for run in sarif.get("runs", []):
        results = run.get("results", [])
        filtered = []
        for r in results:
            rule_id = r.get("ruleId", "")
            if rule_id in EXCLUDED_INSPECTIONS:
                total_removed += 1
                continue
            filtered.append(r)
        run["results"] = filtered

    filtered_sarif.write_text(json.dumps(sarif, indent=2, ensure_ascii=False))
    if total_removed:
        print(f"Excluded {total_removed} InconsistentNaming issue(s)")

    issue_count = sum(len(run.get("results", [])) for run in sarif.get("runs", []))
    return filtered_sarif, issue_count


def print_inspect_summary(sarif_path: Path) -> None:
    if not sarif_path.exists():
        return
    sarif = json.loads(sarif_path.read_text())
    counter: Counter[str] = Counter()
    for run in sarif.get("runs", []):
        for r in run.get("results", []):
            counter[r.get("ruleId", "unknown")] += 1

    if not counter:
        print("  No issues found")
        return
    for rule_id, count in counter.most_common():
        print(f"  {rule_id}: {count}")


# ── similarity-csharp ────────────────────────────────────────────────────


def run_similarity(output_dir: Path, threshold: float) -> tuple[Path, int, int]:
    """Run similarity-csharp and return (report path, group count, total lines)."""
    report_path = output_dir / "similarity.txt"
    assets_dir = TEST_PROJECT / "Assets"

    cmd = [
        "similarity-csharp",
        "-p",
        str(assets_dir),
        "--min-lines",
        "5",
        "--threshold",
        str(threshold),
        "-o",
        str(report_path),
    ]
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"similarity-csharp failed (exit {result.returncode}):")
        if result.stderr:
            print(result.stderr)
        return report_path, 0, 0

    if not report_path.exists():
        print("similarity-csharp produced no output")
        return report_path, 0, 0

    groups, total_lines = parse_similarity_report(report_path)
    return report_path, groups, total_lines


def parse_similarity_report(report_path: Path) -> tuple[int, int]:
    """Parse similarity report to count groups and total impact lines.

    Expected summary line at end of report:
        Found 19 duplicate groups with 48 total methods
        Total impact: 831 duplicate lines
    """
    text = report_path.read_text()
    if not text.strip():
        return 0, 0

    groups = 0
    total_lines = 0

    # Try to parse the summary line at the end
    m_groups = re.search(r"Found\s+(\d+)\s+duplicate groups", text)
    m_lines = re.search(r"Total impact:\s+(\d+)\s+duplicate lines", text)

    if m_groups:
        groups = int(m_groups.group(1))
    if m_lines:
        total_lines = int(m_lines.group(1))

    # Fallback: count "Duplicate Group" headers if summary not found
    if not m_groups:
        groups = text.count("Duplicate Group")

    return groups, total_lines


def print_similarity_summary(groups: int, total_lines: int) -> None:
    if groups == 0:
        print("  No duplicates found")
        return
    print(f"  Duplicate groups: {groups}")
    print(f"  Total affected lines: {total_lines}")


# ── main ─────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="Run static analysis on Unity C# code")
    parser.add_argument(
        "--only",
        choices=["inspect", "similarity"],
        help="Run only the specified tool",
    )
    parser.add_argument(
        "--severity",
        default="WARNING",
        help="inspectcode severity threshold (default: WARNING)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.87,
        help="similarity-csharp threshold (default: 0.87)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Report output directory (default: /tmp)",
    )
    parser.add_argument(
        "--keep-sln",
        action="store_true",
        help="Keep generated .sln after analysis",
    )
    args = parser.parse_args()

    run_inspect = args.only in (None, "inspect")
    run_sim = args.only in (None, "similarity")

    if not ensure_tools(run_inspect, run_sim):
        sys.exit(1)

    output_dir: Path = args.output_dir or Path(tempfile.gettempdir())
    output_dir.mkdir(parents=True, exist_ok=True)

    generated_sln = False
    sln_path: Path | None = None
    if run_inspect and not sln_exists():
        if not find_csproj_files():
            print("No .csproj files found in TestProject/. Open the project in Unity first.")
            sys.exit(1)
        sln_path = generate_sln()
        generated_sln = True

    has_issues = False

    if run_inspect:
        print("\n── inspectcode ──")
        sarif_path, issue_count = run_inspectcode(sln_path or TEST_PROJECT, output_dir, args.severity)
        print(f"\nInspectCode results ({sarif_path}):")
        print_inspect_summary(sarif_path)
        if issue_count > 0:
            has_issues = True

    if run_sim:
        print("\n── similarity-csharp ──")
        report_path, groups, total_lines = run_similarity(output_dir, args.threshold)
        print(f"\nSimilarity results ({report_path}):")
        print_similarity_summary(groups, total_lines)
        if groups > 0:
            has_issues = True

    if generated_sln and not args.keep_sln and sln_path and sln_path.exists():
        sln_path.unlink()
        print(f"\nCleaned up {sln_path.relative_to(ROOT)}")

    sys.exit(1 if has_issues else 0)


if __name__ == "__main__":
    main()
