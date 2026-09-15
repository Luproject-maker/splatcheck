# Contributing to SplatCheck

SplatCheck grows from reproducible interoperability failures. Small, reviewable
contributions with clear provenance are especially useful.

## Report an asset problem

Use the asset compatibility issue form. Include:

- the producer, version, and exact export or conversion command;
- a minimal asset that can legally be redistributed, or an original generator;
- SplatCheck JSON output and the expected result;
- a specification or upstream issue link when one exists;
- a valid control asset when practical.

Never upload private captures, client scenes, faces, locations, or other data
without permission. A synthetic reproducer is preferable when the source asset
cannot be shared.

## Make a change

Use Python 3.10 or newer. The core checker must remain dependency-free and must
not require a GPU or network connection.

```sh
python -m pip install .
python -m unittest discover -v
python tools/run_corpus.py
```

New finding codes should be stable and documented in tests. Unsupported
semantics must fail explicitly rather than being accepted as valid. Add the
smallest fixture that demonstrates the behavior and a valid control.

By contributing, you agree that your contribution is licensed under the MIT
License included in this repository.

