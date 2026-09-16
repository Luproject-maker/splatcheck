# Changelog

## Unreleased

- Added two pinned, CC BY 4.0 real-world PlayCanvas Engine scenes with explicit
  attribution, byte-length and SHA-256 verification.
- Added reproducible SOG → decimated PLY → `KHR_gaussian_splatting` GLB testing
  with `@playcanvas/splat-transform` 3.4.2 and retained Khronos diagnostics.
- Added two real-world GitHub Actions jobs without redistributing scene binaries.

## 0.1.0 — 2026-09-15

- Binary Graphdeco PLY checks, CLI and JSON reports.
- Dense FLOAT KHR GLB SH0–3 checks with bounds and numerical validation.
- Original synthetic corpus and deterministic Khronos comparison adapter.
- Fixed PLY comment/header ambiguity and invalid resource budget handling.
- Reject duplicate JSON keys, nonstandard constants and unsupported projections.
- Cross-platform Python CI and optional external comparison job.
- Reusable GitHub Action with newline-delimited safe glob expansion and optional
  report output.
- Contribution guide, security policy, code of conduct, structured issue form,
  and pull request checklist.

Local verification: 24 unit tests, 5 corpus cases, 4 external comparison cases.
External adoption remains unverified at initial publication.


