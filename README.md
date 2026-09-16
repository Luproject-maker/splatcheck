# SplatCheck

[![checks](https://github.com/Luproject-maker/splatcheck/actions/workflows/ci.yml/badge.svg)](https://github.com/Luproject-maker/splatcheck/actions/workflows/ci.yml)

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

## GitHub Action

Add SplatCheck to another repository without copying scripts. Provide one path or
glob pattern per line; expansion happens without evaluating the input in a shell.

```yaml
name: validate-splats
on: [push, pull_request]

jobs:
  splatcheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-python@v7
        with:
          python-version: '3.12'
      - uses: Luproject-maker/splatcheck@v0.1.0
        with:
          files: |
            assets/**/*.ply
            assets/**/*.glb
          format: json
          report: splatcheck-report.json
```

The action fails the job when a requested asset fails, is unsupported, cannot be
read, or when a pattern matches no file. The optional `report` input writes the
same output printed in the Actions log. Upload it separately with
`actions/upload-artifact` when retention is needed.

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

## Real-world interoperability

The opt-in real-world corpus downloads two pinned, SHA-256-verified PlayCanvas
Engine scenes with explicit CC BY 4.0 attribution. Pinned
`@playcanvas/splat-transform` converts each complete SOG input in CPU mode into a
bounded 5,000-splat PLY sample and then an uncompressed KHR GLB. Both derivatives
are checked by SplatCheck; raw Khronos validator diagnostics are retained separately.
No third-party scene binary or derived asset is committed to this repository.

```sh
npm ci --ignore-scripts
python tools/run_real_interop.py \
  --output docs/real-interop.json \
  --markdown docs/real-interop.md
```

See the [manifest and attribution](interop/README.md) and the
[latest checked-in results](docs/real-interop.md). Network access is required
unless the verified originals are supplied through `--cache-dir` with
`--offline`.

Motivating public reports:

- [GLB scale encoding](https://github.com/playcanvas/splat-transform/issues/267)
- [PLY record misalignment](https://github.com/nerfstudio-project/nerfstudio/issues/3377)
- [KHR specification](https://github.com/KhronosGroup/glTF/blob/main/extensions/2.0/Khronos/KHR_gaussian_splatting/README.md), consulted 2026-09-15.

The repository includes GitHub Actions CI for three OSes and Python versions.
It also runs both pinned real-world cases on Linux. To check your own assets in a
Python-enabled CI:

```sh
python -m splatcheck path/to/export.glb --format json
```

## Contributing

Start with a minimal, redistributable failing asset or an original generator,
the expected error code, producer/version information, and a spec or issue link.
Include a valid control. Do not submit private scenes or files without permission.
Run unit tests and the corpus before opening a change. Add adapters and profiles
incrementally; unknown semantics should remain explicit.

See [CONTRIBUTING.md](CONTRIBUTING.md), the [security policy](SECURITY.md), and
the [code of conduct](CODE_OF_CONDUCT.md) before submitting assets or changes.

MIT licensed. No affiliation with Khronos, PlayCanvas, Nerfstudio or OpenAI.



