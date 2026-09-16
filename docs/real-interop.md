# Real-world interoperability results

Pinned, licensed upstream scenes were processed with `splat-transform v3.4.2 (0cb47cd)` from `@playcanvas/splat-transform`. Derived files are temporary and are not redistributed.

| Case | Source splats | PLY | GLB | Khronos diagnostics |
| --- | ---: | --- | --- | ---: |
| `sa3d-apartment` | 661466 | pass (5000) | pass (5000) | 5 |
| `knock-community-hall` | 1935100 | pass (5000) | pass (5000) | 5 |

## Attribution

- **SA3D_R&D_XP47**, by Stephane Agullo; [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/); [source](https://superspl.at/view?id=cdcec084); [upstream notice](https://github.com/playcanvas/engine/blob/3ee7522039027d98860eec3277220893b5afd871/examples/assets/splats/apartment.txt).
- **Knock Community Hall**, by scbenoit; [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/); [source](https://superspl.at/scene/0ff2e6dc); [upstream notice](https://github.com/playcanvas/engine/blob/3ee7522039027d98860eec3277220893b5afd871/examples/assets/splats/knock-community-hall.txt).

## Interpretation

Both real scenes pass SplatCheck after the pinned producer converts them to the supported Graphdeco PLY and uncompressed KHR GLB profiles. Khronos glTF Validator diagnostics are retained verbatim but are non-gating: the pinned validator reports `UNSUPPORTED_EXTENSION` and generic attribute-name errors because it does not implement `KHR_gaussian_splatting`.

This verifies structural interoperability and numerical invariants, not rendering or visual equivalence. Decimation preserves real input distributions while bounding CI runtime; the derived 5,000-splat files are not substitutes for the complete scenes.

