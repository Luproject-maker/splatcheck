"""Original synthetic fixtures; no downloaded scenes or upstream code."""
import json
import struct


def make_ply(extra=b"", endian="<", newline="\n", sh=0, nonfinite=False):
    fields = ["x", "y", "z", "opacity"] + [f"f_dc_{i}" for i in range(3)]
    fields += [f"scale_{i}" for i in range(3)] + [f"rot_{i}" for i in range(4)]
    fields += [f"f_rest_{i}" for i in range(sh)]
    header = ["ply", f"format binary_{'little' if endian == '<' else 'big'}_endian 1.0", "element vertex 1"]
    header += [f"property float {name}" for name in fields] + ["end_header", ""]
    row = [0.0] * len(fields)
    row[fields.index("scale_0")] = -2.0  # Valid Graphdeco log-scale.
    row[fields.index("opacity")] = -3.0  # Valid Graphdeco logit-opacity.
    row[fields.index("rot_0")] = 1.0
    if nonfinite:
        row[0] = float("nan")
    return newline.join(header).encode() + struct.pack(endian + "f" * len(row), *row) + extra


def make_glb(scale=0.25, opacity=0.5, quaternion=(0, 0, 0, 1), mutate=None):
    rows = [(0, 0, 0), quaternion, (scale, scale, scale), (opacity,), (0, 0, 0)]
    names = ["POSITION"] + ["KHR_gaussian_splatting:" + n for n in ("ROTATION", "SCALE", "OPACITY", "SH_DEGREE_0_COEF_0")]
    binary, views, accessors = b"", [], []
    for row in rows:
        payload = struct.pack("<" + "f" * len(row), *row)
        views.append({"buffer": 0, "byteOffset": len(binary), "byteLength": len(payload)})
        accessors.append({"bufferView": len(views)-1, "componentType": 5126, "count": 1,
                          "type": "SCALAR" if len(row) == 1 else f"VEC{len(row)}"})
        binary += payload
    accessors[0].update(min=[0, 0, 0], max=[0, 0, 0])
    doc = {"asset": {"version": "2.0"}, "extensionsUsed": ["KHR_gaussian_splatting"],
           "buffers": [{"byteLength": len(binary)}], "bufferViews": views, "accessors": accessors,
           "meshes": [{"primitives": [{"mode": 0, "attributes": dict(zip(names, range(5))),
                       "extensions": {"KHR_gaussian_splatting": {"kernel": "ellipse", "colorSpace": "lin_rec709_display"}}}]}],
           "nodes": [{"mesh": 0}], "scenes": [{"nodes": [0]}], "scene": 0}
    if mutate:
        mutate(doc)
    encoded = json.dumps(doc, separators=(",", ":")).encode()
    encoded += b" " * (-len(encoded) % 4)
    return (struct.pack("<4sII", b"glTF", 2, 28 + len(encoded) + len(binary))
            + struct.pack("<I4s", len(encoded), b"JSON") + encoded
            + struct.pack("<I4s", len(binary), b"BIN\0") + binary)
