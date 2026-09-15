"""Run the synthetic manifest against SplatCheck; no files persist."""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from splatcheck import check
from tests.assets import make_glb, make_ply


def main():
    manifest = json.loads((ROOT / "corpus/manifest.json").read_text())
    results = []
    with tempfile.TemporaryDirectory() as folder:
        for case in manifest["cases"]:
            recipe = dict(case["recipe"])
            if "extra" in recipe:
                recipe["extra"] = recipe["extra"].encode()
            data = (make_ply if case["format"] == "ply" else make_glb)(**recipe)
            path = Path(folder) / (case["id"] + "." + case["format"])
            path.write_bytes(data)
            report = check(path)
            actual = "pass" if report["status"] == "pass" else report["findings"][0]["code"]
            results.append({"case": case["id"], "expected": case["expected"], "actual": actual, "matched": actual == case["expected"]})
    print(json.dumps(results, indent=2))
    return 0 if all(r["matched"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
