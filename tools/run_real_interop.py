"""Run pinned real-world assets through an external producer and SplatCheck."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from splatcheck import check


class InteropError(RuntimeError):
    """A reproducibility or external-tool contract failed."""


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_manifest(manifest):
    if manifest.get("schema_version") != 1:
        raise InteropError("Expected interoperability manifest schema_version 1")
    assets = manifest.get("assets")
    if not isinstance(assets, list) or not assets:
        raise InteropError("Manifest must contain at least one asset")
    ids = set()
    filenames = set()
    for asset in assets:
        required = {"id", "filename", "url", "bytes", "sha256", "sample_splats", "license"}
        if not required <= asset.keys():
            raise InteropError(f"Incomplete asset record: {asset.get('id', '<unknown>')}")
        if asset["id"] in ids or asset["filename"] in filenames:
            raise InteropError("Asset IDs and filenames must be unique")
        if Path(asset["filename"]).name != asset["filename"]:
            raise InteropError("Asset filename must not contain a directory")
        if not asset["url"].startswith("https://raw.githubusercontent.com/"):
            raise InteropError("Asset URL must be a pinned raw.githubusercontent.com URL")
        if type(asset["bytes"]) is not int or asset["bytes"] <= 0:
            raise InteropError("Asset byte length must be a positive integer")
        if type(asset["sample_splats"]) is not int or asset["sample_splats"] <= 0:
            raise InteropError("sample_splats must be a positive integer")
        if len(asset["sha256"]) != 64:
            raise InteropError("Asset SHA-256 must contain 64 hexadecimal characters")
        try:
            int(asset["sha256"], 16)
        except ValueError as exc:
            raise InteropError("Asset SHA-256 is not hexadecimal") from exc
        if asset["license"].get("spdx") != "CC-BY-4.0":
            raise InteropError("Real assets require an explicit supported license")
        ids.add(asset["id"])
        filenames.add(asset["filename"])
    return manifest


def load_manifest(path):
    return validate_manifest(json.loads(Path(path).read_text(encoding="utf-8")))


def verify_asset(path, asset):
    path = Path(path)
    actual_bytes = path.stat().st_size
    actual_hash = sha256_file(path)
    if actual_bytes != asset["bytes"]:
        raise InteropError(
            f"{asset['id']} byte length mismatch: expected {asset['bytes']}, found {actual_bytes}"
        )
    if actual_hash.lower() != asset["sha256"].lower():
        raise InteropError(
            f"{asset['id']} SHA-256 mismatch: expected {asset['sha256']}, found {actual_hash}"
        )
    return {"bytes": actual_bytes, "sha256": actual_hash}


def acquire_asset(asset, cache_dir, offline=False):
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    destination = cache_dir / asset["filename"]
    if destination.exists():
        verify_asset(destination, asset)
        return destination
    if offline:
        raise InteropError(f"Offline cache miss: {destination}")

    partial = destination.with_name(destination.name + ".part")
    partial.unlink(missing_ok=True)
    request = urllib.request.Request(
        asset["url"], headers={"User-Agent": "splatcheck-real-interop/1"}
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response, partial.open("wb") as output:
            total = 0
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > asset["bytes"]:
                    raise InteropError(f"{asset['id']} download exceeds pinned byte length")
                output.write(chunk)
        verify_asset(partial, asset)
        os.replace(partial, destination)
    finally:
        partial.unlink(missing_ok=True)
    return destination


def node_cli():
    node = shutil.which("node")
    cli = ROOT / "node_modules" / "@playcanvas" / "splat-transform" / "bin" / "cli.mjs"
    if not node:
        raise InteropError("Node.js was not found on PATH")
    if not cli.is_file():
        raise InteropError("Run 'npm ci --ignore-scripts' before the real-world corpus")
    return [node, str(cli)]


def run_checked(command, timeout):
    result = subprocess.run(
        command, capture_output=True, text=True, timeout=timeout, check=False
    )
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise InteropError(f"External command failed ({result.returncode}): {detail}")
    return result.stdout if result.stdout.strip() else result.stderr


def tool_info(cli, source, timeout):
    return json.loads(
        run_checked(
            cli + ["-q", "--gpu", "cpu", str(source), "--info", "json", "null"],
            timeout,
        )
    )


def normalized_check(path):
    report = check(path)
    report["file"] = Path(path).name
    return report


def write_utf8(path, content):
    """Write reproducible LF-only reports on every operating system."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(content)


def run_case(asset, cache_dir, derived_dir, cli, timeout, offline):
    source = acquire_asset(asset, cache_dir, offline=offline)
    source_verification = verify_asset(source, asset)
    info = tool_info(cli, source, timeout)
    case_dir = Path(derived_dir) / asset["id"]
    case_dir.mkdir(parents=True, exist_ok=True)
    ply = case_dir / f"{asset['id']}.ply"
    glb = case_dir / f"{asset['id']}.glb"

    run_checked(
        cli
        + [
            "-q",
            "-w",
            "--gpu",
            "cpu",
            str(source),
            "--filter-harmonics",
            "0",
            "--decimate",
            str(asset["sample_splats"]),
            str(ply),
        ],
        timeout,
    )
    run_checked(cli + ["-q", "-w", "--gpu", "cpu", str(ply), str(glb)], timeout)

    ply_report = normalized_check(ply)
    glb_report = normalized_check(glb)
    khronos = json.loads(
        run_checked([cli[0], str(ROOT / "tools" / "khronos.cjs"), str(glb)], timeout)
    )
    expected = asset["sample_splats"]
    failures = []
    if info.get("gaussian") is not True or info.get("numGaussians", 0) < expected:
        failures.append("source metadata is not a sufficiently large Gaussian scene")
    for name, report in (("PLY", ply_report), ("GLB", glb_report)):
        if report["status"] != "pass":
            failures.append(f"{name} failed SplatCheck")
        if report.get("splats") != expected:
            failures.append(f"{name} splat count differs from {expected}")

    return {
        "id": asset["id"],
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "license": asset["license"],
        "source": {
            "filename": asset["filename"],
            "url": asset["url"],
            **source_verification,
            "producer_info": info,
        },
        "pipeline": [
            f"SOG -> SH0 {expected}-splat CPU-decimated binary PLY",
            "binary PLY -> uncompressed KHR_gaussian_splatting GLB",
        ],
        "derived": [
            {
                "format": "ply",
                "bytes": ply.stat().st_size,
                "sha256": sha256_file(ply),
                "splatcheck": ply_report,
            },
            {
                "format": "glb",
                "bytes": glb.stat().st_size,
                "sha256": sha256_file(glb),
                "splatcheck": glb_report,
                "khronos": khronos,
            },
        ],
    }


def render_markdown(report):
    lines = [
        "# Real-world interoperability results",
        "",
        f"Pinned, licensed upstream scenes were processed with `{report['tool']['actual_version']}` "
        f"from `{report['tool']['package']}`. Derived files are temporary and are not redistributed.",
        "",
        "| Case | Source splats | PLY | GLB | Khronos diagnostics |",
        "| --- | ---: | --- | --- | ---: |",
    ]
    for case in report["cases"]:
        ply, glb = case["derived"]
        issues = glb["khronos"]["issues"]
        messages = issues["numErrors"] + issues["numWarnings"] + issues["numInfos"] + issues["numHints"]
        lines.append(
            f"| `{case['id']}` | {case['source']['producer_info']['numGaussians']} | "
            f"{ply['splatcheck']['status']} ({ply['splatcheck'].get('splats', 0)}) | "
            f"{glb['splatcheck']['status']} ({glb['splatcheck'].get('splats', 0)}) | {messages} |"
        )
    lines += [
        "",
        "## Attribution",
        "",
    ]
    for case in report["cases"]:
        license_info = case["license"]
        lines.append(
            f"- **{license_info['title']}**, by {license_info['author']}; "
            f"[{license_info['spdx']}](https://creativecommons.org/licenses/by/4.0/); "
            f"[source]({license_info['source']}); [upstream notice]({license_info['notice']})."
        )
    lines += [
        "",
        "## Interpretation",
        "",
        "Both real scenes pass SplatCheck after the pinned producer converts them to the supported "
        "Graphdeco PLY and uncompressed KHR GLB profiles. Khronos glTF Validator diagnostics are "
        "retained verbatim but are non-gating: the pinned validator reports `UNSUPPORTED_EXTENSION` "
        "and generic attribute-name errors because it does not implement `KHR_gaussian_splatting`.",
        "",
        "This verifies structural interoperability and numerical invariants, not rendering or visual "
        "equivalence. Decimation preserves real input distributions while bounding CI runtime; the "
        "derived 5,000-splat files are not substitutes for the complete scenes.",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Run licensed real Gaussian scenes through pinned tools")
    parser.add_argument("--manifest", type=Path, default=ROOT / "interop" / "manifest.json")
    parser.add_argument("--asset", action="append", dest="assets")
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--markdown", type=Path)
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be positive")

    manifest = load_manifest(args.manifest)
    selected = manifest["assets"]
    if args.assets:
        wanted = set(args.assets)
        known = {asset["id"] for asset in selected}
        if not wanted <= known:
            parser.error("unknown --asset value: " + ", ".join(sorted(wanted - known)))
        selected = [asset for asset in selected if asset["id"] in wanted]

    cli = node_cli()
    actual_version = run_checked(cli + ["--version"], args.timeout).strip()
    expected_prefix = f"splat-transform v{manifest['tool']['version']} "
    if not actual_version.startswith(expected_prefix):
        raise InteropError(
            f"Expected {expected_prefix.strip()}, found {actual_version or '<empty>'}"
        )
    temporary_cache = tempfile.TemporaryDirectory() if args.cache_dir is None else None
    cache_dir = args.cache_dir or Path(temporary_cache.name)
    try:
        with tempfile.TemporaryDirectory() as derived_dir:
            cases = [
                run_case(asset, cache_dir, derived_dir, cli, args.timeout, args.offline)
                for asset in selected
            ]
    finally:
        if temporary_cache is not None:
            temporary_cache.cleanup()

    report = {
        "schema_version": 1,
        "scope": "Pinned CC BY 4.0 real scenes; temporary 5,000-splat derivatives",
        "upstream": manifest["upstream"],
        "tool": {**manifest["tool"], "actual_version": actual_version},
        "summary": {
            "cases": len(cases),
            "passed": sum(case["status"] == "pass" for case in cases),
        },
        "cases": cases,
    }
    encoded = json.dumps(report, indent=2) + "\n"
    if args.output:
        write_utf8(args.output, encoded)
    else:
        print(encoded, end="")
    if args.markdown:
        write_utf8(args.markdown, render_markdown(report))
    return 0 if report["summary"]["passed"] == len(cases) else 1


if __name__ == "__main__":
    raise SystemExit(main())

