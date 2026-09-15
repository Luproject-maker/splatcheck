import json
import io
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from splatcheck import check
from tests.assets import make_glb, make_ply


class Checks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def asset(self, data, suffix):
        p = Path(self.temp.name) / ("asset" + suffix)
        p.write_bytes(data)
        return p

    def expect(self, data, suffix, code=None):
        report = check(self.asset(data, suffix))
        if code:
            self.assertEqual(report["findings"][0]["code"], code, report)
        else:
            self.assertEqual(report["status"], "pass", report)

    def test_ply_valid_conventions(self):
        for endian in ("<", ">"):
            for newline in ("\n", "\r\n"):
                for sh in (0, 9, 24, 45):
                    with self.subTest(endian=endian, newline=newline, sh=sh):
                        self.expect(make_ply(endian=endian, newline=newline, sh=sh), ".ply")

    def test_ply_layout_regression(self):
        self.expect(make_ply(extra=b"rgb"), ".ply", "PLY_PAYLOAD_SIZE_MISMATCH")

    def test_ply_nan(self):
        self.expect(make_ply(nonfinite=True), ".ply", "NONFINITE_VALUE")

    def test_ply_incomplete_sh(self):
        self.expect(make_ply(sh=8), ".ply", "PLY_SH_INVALID")

    def test_glb_valid(self):
        self.expect(make_glb(), ".glb")

    def test_glb_scale_regression(self):
        self.expect(make_glb(scale=-2), ".glb", "KHR_SCALE_NEGATIVE")

    def test_glb_opacity(self):
        self.expect(make_glb(opacity=2), ".glb", "KHR_OPACITY_RANGE")

    def test_glb_quaternion(self):
        self.expect(make_glb(quaternion=(0, 0, 0, 0)), ".glb", "KHR_ROTATION_NORM")

    def test_glb_nan(self):
        self.expect(make_glb(scale=float("nan")), ".glb", "NONFINITE_VALUE")

    def test_glb_accessor_bounds(self):
        self.expect(make_glb(mutate=lambda d: d["accessors"][2].update(byteOffset=100)),
                    ".glb", "ACCESSOR_BOUNDS_INVALID")

    def test_glb_negative_reference(self):
        self.expect(make_glb(mutate=lambda d: d["accessors"][2].update(bufferView=-1)),
                    ".glb", "STRUCTURE_INVALID")

    def test_glb_unsupported_quantization(self):
        self.expect(make_glb(mutate=lambda d: d["accessors"][2].update(componentType=5123)),
                    ".glb", "UNSUPPORTED_PROFILE")

    def test_all_truncations_fail_without_crash(self):
        for suffix, blob in ((".ply", make_ply()), (".glb", make_glb())):
            for length in range(len(blob)):
                with patch.object(Path, "open", return_value=io.BytesIO(blob[:length])):
                    r = check(Path("truncated" + suffix))
                self.assertNotEqual(r["status"], "pass", (suffix, length))

    def test_resource_limit(self):
        r = check(self.asset(make_ply(), ".ply"), max_bytes=8)
        self.assertEqual(r["findings"][0]["code"], "RESOURCE_LIMIT")

    def test_negative_resource_limit(self):
        r = check("unused.ply", max_bytes=-2)
        self.assertEqual(r["findings"][0]["code"], "RESOURCE_LIMIT")

    def test_header_comment_with_terminator_text(self):
        data = make_ply().replace(b"element vertex", b"comment end_header\nelement vertex")
        self.expect(data, ".ply")

    def test_complete_higher_sh(self):
        def add_sh(doc):
            attrs = doc["meshes"][0]["primitives"][0]["attributes"]
            for degree in (1, 2, 3):
                for i in range(2*degree+1):
                    attrs[f"KHR_gaussian_splatting:SH_DEGREE_{degree}_COEF_{i}"] = 4
        self.expect(make_glb(mutate=add_sh), ".glb")

    def test_missing_lower_sh(self):
        def add_sh(doc):
            attrs = doc["meshes"][0]["primitives"][0]["attributes"]
            for i in range(5):
                attrs[f"KHR_gaussian_splatting:SH_DEGREE_2_COEF_{i}"] = 4
        self.expect(make_glb(mutate=add_sh), ".glb", "KHR_SH_INVALID")

    def test_unsupported_projection(self):
        def edit(doc):
            doc["meshes"][0]["primitives"][0]["extensions"]["KHR_gaussian_splatting"]["projection"] = "other"
        self.expect(make_glb(mutate=edit), ".glb", "UNSUPPORTED_PROFILE")

    def test_missing_file(self):
        self.assertEqual(check(Path(self.temp.name) / "missing.ply")["status"], "error")

    def test_cli_exit_and_json(self):
        for data, expected in ((make_glb(), 0), (make_glb(scale=-2), 1)):
            p = self.asset(data, ".glb")
            result = subprocess.run([sys.executable, "-m", "splatcheck", str(p), "--format", "json"], capture_output=True, text=True)
            self.assertEqual(result.returncode, expected, result.stderr)
            self.assertEqual(json.loads(result.stdout)["schema_version"], 1)


if __name__ == "__main__":
    unittest.main()
