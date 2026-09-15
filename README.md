# SplatCheck

CPU-only Gaussian Splatting checks with an original synthetic regression corpus.
Version 0.1 is an experimental, dependency-free Python CLI. No GPU, training,
network requests or asset uploads are required.

## Quick start

Python 3.10 or newer:

```sh
python -m splatcheck scene.ply scene.glb
python -m splatcheck scene.glb --format json
python -m pip install .
splatcheck scene.ply
```

Exit code 0 means the supported checks passed. Exit code 1 means a failed,
unsupported or unreadable asset. Argument errors return 2. JSON reports include
`schema_version`, per-file status, profile, and stable finding codes.

## Supported checks

| Profile | Coverage |
| --- | --- |
| Graphdeco 3DGS binary PLY | Little/big endian, LF/CRLF, scalar vertex fields, payload length, finite values, SH0-3 layout |
| KHR Gaussian Splatting GLB | Embedded buffer, uncompressed ellipse, dense FLOAT accessors, SH0–3, bounds/stride, required attributes, non-negative scale, opacity range, quaternion norm |

Graphdeco PLY scale and opacity are log/logit parameters. Negative values are
normal there. KHR GLB uses linear scale and opacity. Negative GLB scale is invalid,
but positive values alone cannot prove that the correct encoding was used.

This is **not a full glTF conformance certificate**. Use Khronos glTF Validator
alongside it. Scene/node transforms, visual equivalence,
quantized/sparse accessors, compression extensions, 2DGS, ASCII/list-element PLY,
SPZ and SOG are outside v0.1. Unsupported layouts fail closed. PLY checks assume
the documented Graphdeco dialect; coordinates and quaternion ordering cannot be
inferred from arbitrary unlabelled values. Files are limited to 256 MiB and loaded
into memory. Reports stop at the first blocking finding per file.

## Regression corpus

```sh
python tools/run_corpus.py
python -m unittest discover -v
```

`corpus/manifest.json` records expected outcomes. `tests/assets.py` generates tiny
original assets, including valid controls. These are synthetic reproductions of
failure classes, not original affected user files or verified upstream reproducers.
The corpus runner tests SplatCheck. A separate optional adapter compares four GLB
fixtures with the pinned Khronos npm validator:

```sh
npm ci --ignore-scripts
python tools/compare.py --output docs/comparison.json
```

See [comparison findings](docs/comparison.md). Node is needed only for this adapter.

Motivating public reports:

- [GLB scale encoding](https://github.com/playcanvas/splat-transform/issues/267)
- [PLY record misalignment](https://github.com/nerfstudio-project/nerfstudio/issues/3377)
- [KHR specification](https://github.com/KhronosGroup/glTF/blob/main/extensions/2.0/Khronos/KHR_gaussian_splatting/README.md), consulted 2026-09-15.

The repository includes GitHub Actions CI for three OSes and Python versions.
It runs once the repository is hosted on GitHub; local tests do not establish
that the hosted matrix has passed. To check your own assets in a Python-enabled CI:

```sh
python -m splatcheck path/to/export.glb --format json
```

## Contributing

Start with a minimal, redistributable failing asset or an original generator,
the expected error code, producer/version information, and a spec or issue link.
Include a valid control. Do not submit private scenes or files without permission.
Run unit tests and the corpus before opening a change. Add adapters and profiles
incrementally; unknown semantics should remain explicit.

MIT licensed. No affiliation with Khronos, PlayCanvas, Nerfstudio or OpenAI.
