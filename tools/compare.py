"""Reproducible comparison; retains limitations and raw external diagnostics."""
import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from splatcheck import check
from tests.assets import make_glb


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    recipes = {"valid": {}, "negative-scale": {"scale": -2},
               "opacity-out-of-range": {"opacity": 2}, "zero-quaternion": {"quaternion": (0, 0, 0, 0)}}
    report = {"schema_version": 1, "scope": "Synthetic GLB fixtures only; not an adoption or upstream regression claim", "cases": []}
    with tempfile.TemporaryDirectory() as directory:
        for name, recipe in recipes.items():
            data = make_glb(**recipe)
            path = Path(directory) / (name + ".glb")
            path.write_bytes(data)
            result = subprocess.run(["node", str(ROOT / "tools/khronos.cjs"), str(path)],
                                    capture_output=True, text=True, timeout=30)
            if result.returncode:
                raise RuntimeError(f"Khronos adapter failed: {result.stderr}")
            ours = check(path)
            ours["file"] = path.name
            report["cases"].append({"id": name, "sha256": hashlib.sha256(data).hexdigest(),
                                    "splatcheck": ours, "khronos": json.loads(result.stdout)})
    encoded = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded + "\n", encoding="utf-8")
    else:
        print(encoded)


if __name__ == "__main__":
    main()
