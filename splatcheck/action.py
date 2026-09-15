"""Safe entry point for the SplatCheck composite GitHub Action."""

import glob
import os
import subprocess
import sys
from pathlib import Path


def expand_patterns(spec):
    """Expand one path or glob per line, preserving unmatched paths for diagnostics."""
    expanded = []
    seen = set()
    for line in spec.splitlines():
        pattern = line.strip()
        if not pattern:
            continue
        matches = [path for path in glob.glob(pattern, recursive=True) if Path(path).is_file()]
        for path in matches or [pattern]:
            if path not in seen:
                seen.add(path)
                expanded.append(path)
    return expanded


def main():
    files = expand_patterns(os.environ.get("SPLATCHECK_FILES", ""))
    report_format = os.environ.get("SPLATCHECK_FORMAT", "text").strip().lower()
    report_path = os.environ.get("SPLATCHECK_REPORT", "").strip()

    if not files:
        print("SPLATCHECK_FILES must contain at least one path or glob pattern", file=sys.stderr)
        return 2
    if report_format not in ("text", "json"):
        print("SPLATCHECK_FORMAT must be text or json", file=sys.stderr)
        return 2

    result = subprocess.run(
        [sys.executable, "-m", "splatcheck", *files, "--format", report_format],
        capture_output=True,
        text=True,
        check=False,
    )
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)

    if report_path:
        destination = Path(report_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(result.stdout, encoding="utf-8")
        print(f"Report written to {destination}", file=sys.stderr)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())

