# Real-world interoperability corpus

This directory contains metadata, not third-party scene binaries. The runner
downloads two pinned PlayCanvas Engine assets after verifying their byte length
and SHA-256 digest. Both assets include upstream CC BY 4.0 notices:

- **SA3D_R&D_XP47**, by Stephane Agullo;
- **Knock Community Hall**, by scbenoit.

The pinned `@playcanvas/splat-transform` CLI reads each real SOG scene, removes
higher SH bands if present, decimates it in CPU mode to 5,000 representative
splats, writes a Graphdeco-style binary PLY, and converts that PLY to an uncompressed
`KHR_gaussian_splatting` GLB. SplatCheck validates both derived files. Khronos
glTF Validator diagnostics are retained separately and are non-gating because
the pinned validator does not implement the release-candidate extension.

```sh
npm ci --ignore-scripts
python tools/run_real_interop.py \
  --output docs/real-interop.json \
  --markdown docs/real-interop.md
```

Use `--asset sa3d-apartment` to run one case, `--cache-dir PATH` to retain
verified downloads, or `--offline` to forbid network access. Derived assets live
only in a temporary directory and are not redistributed by this repository.

