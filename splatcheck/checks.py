"""Bounded, read-only checks. Unsupported layouts never silently pass."""
import json
import math
import struct
from pathlib import Path

KHR = "KHR_gaussian_splatting"
LIMIT = 256 * 1024 * 1024


class Invalid(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def require(condition, code, message):
    if not condition:
        raise Invalid(code, message)


def integer(value):
    require(type(value) is int and value >= 0, "STRUCTURE_INVALID", "Expected non-negative integer")
    return value


def item(items, index):
    index = integer(index)
    require(index < len(items), "REFERENCE_INVALID", "Index outside array")
    return items[index]


def ply(data):
    end, marker, offset = -1, 0, 0
    for line in data[:65536].splitlines(keepends=True):
        if line in (b"end_header\n", b"end_header\r\n"):
            end, marker = offset, len(line)
            break
        offset += len(line)
    require(end >= 0, "PLY_HEADER_INVALID", "Missing header terminator within 64 KiB")
    lines = data[:end].decode("ascii").splitlines()
    require(lines[0] == "ply", "PLY_HEADER_INVALID", "Expected ply magic")
    require(len(lines) > 1 and lines[1] in (
        "format binary_little_endian 1.0", "format binary_big_endian 1.0"
    ), "UNSUPPORTED_PROFILE", "Only binary PLY is supported")
    count, props = None, []
    types = {"float": "f", "float32": "f", "double": "d", "float64": "d",
             "uchar": "B", "uint8": "B", "char": "b", "int8": "b",
             "short": "h", "int16": "h", "ushort": "H", "uint16": "H",
             "int": "i", "int32": "i", "uint": "I", "uint32": "I"}
    for line in lines[2:]:
        p = line.split()
        if not p or p[0] in ("comment", "obj_info"):
            continue
        if p[0] == "element":
            require(len(p) == 3 and p[1] == "vertex" and count is None,
                    "UNSUPPORTED_PROFILE", "Only one vertex element is supported")
            count = integer(int(p[2]))
        elif p[0] == "property":
            require(count is not None and len(p) == 3 and p[1] in types,
                    "UNSUPPORTED_PROFILE", "Only scalar vertex properties are supported")
            require(p[2] not in [name for name, _ in props], "PLY_HEADER_INVALID", "Duplicate property")
            props.append((p[2], types[p[1]]))
        else:
            raise Invalid("PLY_HEADER_INVALID", "Unknown header directive")
    require(count is not None and props, "PLY_HEADER_INVALID", "Missing vertex declaration")
    layout = struct.Struct(("<" if "little" in lines[1] else ">") + "".join(t for _, t in props))
    payload = memoryview(data)[end + marker:]
    require(len(payload) == count * layout.size, "PLY_PAYLOAD_SIZE_MISMATCH",
            f"Expected {count * layout.size} payload bytes, found {len(payload)}")
    names = {name for name, _ in props}
    required = {"x", "y", "z", "opacity", *[f"f_dc_{i}" for i in range(3)],
                *[f"scale_{i}" for i in range(3)], *[f"rot_{i}" for i in range(4)]}
    require(required <= names, "UNSUPPORTED_PROFILE", "Expected Graphdeco 3DGS fields (2DGS not supported yet)")
    sh = {n for n in names if n.startswith("f_rest_")}
    require(len(sh) in (0, 9, 24, 45) and sh == {f"f_rest_{i}" for i in range(len(sh))},
            "PLY_SH_INVALID", "Expected contiguous SH degree 0-3 coefficients")
    for row in layout.iter_unpack(payload):
        require(all(math.isfinite(v) for v in row), "NONFINITE_VALUE", "PLY contains NaN or infinity")
    return {"profile": "graphdeco-ply", "splats": count}


def glb(data):
    require(len(data) >= 20, "GLB_CONTAINER_INVALID", "Truncated GLB header")
    magic, version, size = struct.unpack_from("<4sII", data)
    require(magic == b"glTF" and version == 2 and size == len(data),
            "GLB_CONTAINER_INVALID", "Invalid GLB magic, version or length")
    chunks, pos = [], 12
    while pos < len(data):
        require(pos + 8 <= len(data), "GLB_CONTAINER_INVALID", "Truncated chunk header")
        size, kind = struct.unpack_from("<I4s", data, pos)
        pos += 8
        require(size % 4 == 0 and pos + size <= len(data), "GLB_CONTAINER_INVALID", "Invalid chunk bounds/alignment")
        chunks.append((kind, memoryview(data)[pos:pos + size]))
        pos += size
    require([k for k, _ in chunks] == [b"JSON", b"BIN\0"],
            "UNSUPPORTED_PROFILE", "Expected one JSON and one embedded BIN chunk")
    def object_pairs(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "STRUCTURE_INVALID", "Duplicate JSON key")
            result[key] = value
        return result

    def invalid_constant(value):
        raise Invalid("STRUCTURE_INVALID", f"Invalid JSON constant: {value}")

    doc = json.loads(bytes(chunks[0][1]), object_pairs_hook=object_pairs, parse_constant=invalid_constant)
    binary = chunks[1][1]
    require(doc["asset"]["version"] == "2.0", "STRUCTURE_INVALID", "Expected glTF 2.0")
    require(KHR in doc.get("extensionsUsed", []), "KHR_DECLARATION_MISSING", "Missing extensionsUsed entry")
    require(len(doc["buffers"]) == 1 and "uri" not in doc["buffers"][0],
            "UNSUPPORTED_PROFILE", "Only embedded buffers are supported")
    buffer_size = integer(doc["buffers"][0]["byteLength"])
    require(0 <= len(binary) - buffer_size <= 3, "GLB_BUFFER_INVALID", "BIN length disagrees with buffer")

    def values(index, shape):
        a = item(doc["accessors"], index)
        require("sparse" not in a and a["componentType"] == 5126 and not a.get("normalized", False),
                "UNSUPPORTED_PROFILE", "Only dense FLOAT accessors are supported")
        require(a["type"] == shape, "ACCESSOR_SHAPE_INVALID", f"Expected {shape}")
        v = item(doc["bufferViews"], a["bufferView"])
        require(v["buffer"] == 0, "REFERENCE_INVALID", "Expected buffer 0")
        start, length = integer(v.get("byteOffset", 0)), integer(v["byteLength"])
        offset, count = integer(a.get("byteOffset", 0)), integer(a["count"])
        width = {"VEC3": 3, "VEC4": 4, "SCALAR": 1}[shape]
        stride = integer(v.get("byteStride", width * 4))
        require(count > 0 and stride >= width * 4 and stride <= 252 and stride % 4 == 0
                and start % 4 == 0 and offset % 4 == 0, "ACCESSOR_LAYOUT_INVALID", "Invalid count, stride or alignment")
        require(start + length <= buffer_size and offset + (count - 1) * stride + width * 4 <= length,
                "ACCESSOR_BOUNDS_INVALID", "Accessor exceeds its buffer view")
        def rows():
            for i in range(count):
                row = struct.unpack_from(f"<{width}f", binary, start + offset + i * stride)
                require(all(math.isfinite(x) for x in row), "NONFINITE_VALUE", "Accessor contains NaN or infinity")
                yield row
        return count, rows()

    total = 0
    for mesh in doc.get("meshes", []):
        for p in mesh["primitives"]:
            ext = p.get("extensions", {}).get(KHR)
            if ext is None:
                continue
            require(ext.get("kernel") == "ellipse" and not ext.get("extensions"),
                    "UNSUPPORTED_PROFILE", "Only uncompressed ellipse splats are supported")
            require(ext.get("colorSpace") in ("lin_rec709_display", "srgb_rec709_display"),
                    "UNSUPPORTED_PROFILE", "Unsupported or missing colorSpace")
            require(ext.get("projection", "perspective") == "perspective"
                    and ext.get("sortingMethod", "cameraDistance") == "cameraDistance",
                    "UNSUPPORTED_PROFILE", "Unsupported projection or sorting method")
            require(p.get("mode", 4) == 0, "KHR_MODE_INVALID", "Splat primitive must use POINTS")
            attrs = p["attributes"]
            specs = {"POSITION": "VEC3", KHR + ":ROTATION": "VEC4", KHR + ":SCALE": "VEC3",
                     KHR + ":OPACITY": "SCALAR", KHR + ":SH_DEGREE_0_COEF_0": "VEC3"}
            require(specs.keys() <= attrs.keys(), "KHR_ATTRIBUTE_MISSING", "Missing required Gaussian attribute")
            sh_names = {k for k in attrs if k.startswith(KHR + ":SH_DEGREE_")}
            wanted = {KHR + ":SH_DEGREE_0_COEF_0"}
            for degree in (1, 2, 3):
                group = {f"{KHR}:SH_DEGREE_{degree}_COEF_{i}" for i in range(2 * degree + 1)}
                if sh_names & group:
                    lower = {f"{KHR}:SH_DEGREE_{d}_COEF_{i}" for d in range(degree) for i in range(2*d + 1)}
                    require(lower <= sh_names and group <= sh_names,
                            "KHR_SH_INVALID", "SH degrees must be complete, with all lower degrees")
                    wanted |= group
                    specs.update({name: "VEC3" for name in sorted(group)})
            require(sh_names == wanted, "KHR_SH_INVALID", "Unknown or incomplete SH attribute")
            expected_count = None
            for name, shape in specs.items():
                count, rows = values(attrs[name], shape)
                require(expected_count is None or count == expected_count, "ACCESSOR_COUNT_MISMATCH", "Gaussian attribute counts differ")
                expected_count = count
                for row in rows:
                    if name.endswith(":SCALE"):
                        require(min(row) >= 0, "KHR_SCALE_NEGATIVE", "KHR scale must be linear and non-negative; log encoding may be the cause")
                    elif name.endswith(":OPACITY"):
                        require(0 <= row[0] <= 1, "KHR_OPACITY_RANGE", "KHR opacity must be linear in [0, 1]")
                    elif name.endswith(":ROTATION"):
                        require(abs(sum(x*x for x in row) - 1) <= 0.002, "KHR_ROTATION_NORM", "KHR rotation must be a unit quaternion")
            total += expected_count
    require(total > 0, "KHR_PRIMITIVE_MISSING", "No supported Gaussian primitive found")
    return {"profile": "khr-glb-float-sh0-3", "splats": total}


def check(path, max_bytes=LIMIT):
    """Return a JSON-compatible report; at most one blocking finding per file."""
    path = Path(path)
    report = {"file": str(path), "status": "pass", "findings": []}
    try:
        require(type(max_bytes) is int and max_bytes > 0, "RESOURCE_LIMIT", "Byte limit must be a positive integer")
        require(path.suffix.lower() in (".ply", ".glb"), "UNSUPPORTED_PROFILE", "Expected .ply or .glb")
        with path.open("rb") as stream:
            data = stream.read(max_bytes + 1)
        require(len(data) <= max_bytes, "RESOURCE_LIMIT", "File exceeds byte limit")
        report.update((ply if path.suffix.lower() == ".ply" else glb)(data))
    except Invalid as exc:
        report["status"] = "unsupported" if exc.code == "UNSUPPORTED_PROFILE" else "fail"
        report["findings"] = [{"code": exc.code, "message": str(exc)}]
    except OSError as exc:
        report.update(status="error", findings=[{"code": "IO_ERROR", "message": str(exc)}])
    except (ValueError, KeyError, TypeError, IndexError, AttributeError, struct.error, OverflowError, RecursionError) as exc:
        report.update(status="fail", findings=[{"code": "STRUCTURE_INVALID", "message": str(exc)}])
    return report
