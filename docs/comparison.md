# External comparison

Run locally on Windows, 2026-09-15, with `gltf-validator` npm version
`2.0.0-dev.3.10` (exact dependency and integrity in package-lock.json).

| Synthetic case | SplatCheck | Khronos pinned npm validator |
| --- | --- | --- |
| Valid FLOAT SH0 control | Pass | Unsupported KHR extension; 4 invalid-attribute errors |
| Negative linear scale | KHR_SCALE_NEGATIVE | Same extension/attribute diagnostics |
| Opacity above 1 | KHR_OPACITY_RANGE | Same extension/attribute diagnostics |
| Zero quaternion | KHR_ROTATION_NORM | Same extension/attribute diagnostics |

The raw, unfiltered [report](comparison.json) includes fixture SHA-256 hashes,
version and all external diagnostics. The pinned validator cannot distinguish
these Gaussian-specific semantic mutations. It does **not** pass the malformed
assets: it reports generic extension/attribute issues even for the control.
This is complementary coverage, not evidence that SplatCheck replaces a general
glTF validator. Results do not describe newer builds or other assets.

Reproduce from the repository root with Node and Python installed:

```sh
npm ci --ignore-scripts
python tools/compare.py --output docs/comparison.json
```

The adapter uses the [official validator](https://github.com/KhronosGroup/glTF-Validator)
locally, with a 30-second per-file timeout and no remote resource loading.
CI captures reports; no external maintainers have adopted this corpus yet.
