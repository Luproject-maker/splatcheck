import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.run_real_interop import InteropError, load_manifest, render_markdown, verify_asset


ROOT = Path(__file__).resolve().parents[1]


class RealInteropMetadata(unittest.TestCase):
    def test_manifest_has_pinned_licensed_assets(self):
        manifest = load_manifest(ROOT / "interop" / "manifest.json")
        self.assertEqual(len(manifest["assets"]), 2)
        self.assertEqual(manifest["tool"]["version"], "3.4.2")
        for asset in manifest["assets"]:
            self.assertEqual(asset["license"]["spdx"], "CC-BY-4.0")
            self.assertIn(manifest["upstream"]["commit"], asset["url"])

    def test_asset_verification_rejects_changed_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "asset.sog"
            path.write_bytes(b"licensed-real-asset-placeholder")
            asset = {
                "id": "fixture",
                "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            self.assertEqual(verify_asset(path, asset)["bytes"], path.stat().st_size)
            asset["sha256"] = "0" * 64
            with self.assertRaises(InteropError):
                verify_asset(path, asset)

    def test_markdown_uses_result_counts_and_attribution(self):
        report = {
            "tool": {"package": "producer", "actual_version": "v1"},
            "cases": [{
                "id": "scene",
                "source": {"producer_info": {"numGaussians": 10}},
                "license": {"title": "Scene", "author": "Author", "spdx": "CC-BY-4.0",
                            "source": "https://example.com", "notice": "https://example.com/license"},
                "derived": [
                    {"splatcheck": {"status": "pass", "splats": 5}},
                    {"splatcheck": {"status": "pass", "splats": 5},
                     "khronos": {"issues": {"numErrors": 1, "numWarnings": 2,
                                              "numInfos": 3, "numHints": 4}}},
                ],
            }],
        }
        rendered = render_markdown(report)
        self.assertIn("| `scene` | 10 | pass (5) | pass (5) | 10 |", rendered)
        self.assertIn("**Scene**, by Author", rendered)


if __name__ == "__main__":
    unittest.main()

