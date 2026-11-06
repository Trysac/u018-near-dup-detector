# near-dup-detector

[![PyPI version](https://img.shields.io/pypi/v/trysac-near-dup-detector)](https://pypi.org/project/trysac-near-dup-detector/)
[![License: MIT](https://img.shields.io/pypi/l/trysac-near-dup-detector)](LICENSE)
[![CI](https://github.com/Trysac/u018-near-dup-detector/actions/workflows/ci.yml/badge.svg)](https://github.com/Trysac/u018-near-dup-detector/actions/workflows/ci.yml)

Detect near-duplicate documents with process-stable MinHash and LSH banding plus 64-bit SimHash, verified candidate pairs and deterministic clusters

## Problem

Describe in two or three sentences the concrete problem this utility solves, who hits it, and what
they do today without it. Replace this paragraph when the first real feature lands.

## Install

```sh
pip install trysac-near-dup-detector
# or
uv add trysac-near-dup-detector
```

Requires Python 3.10 or newer. No runtime dependencies.

## Usage

```python
import near_dup_detector

# normalize() trims surrounding whitespace and lower-cases the text.
print(near_dup_detector.normalize("  Hello World "))  # -> "hello world"

# Blank input is rejected explicitly instead of returning an empty string.
try:
    near_dup_detector.normalize("   ")
except ValueError as exc:
    print(f"rejected: {exc}")
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) and [decisions](docs/decisions/)
- [Testing](docs/TESTING.md) and [security](docs/SECURITY.md)
- [Project record](docs/PROJECT.md) and [stack](docs/STACK.md)
- [Changelog](CHANGELOG.md) and [contributing guide](CONTRIBUTING.md)

## License

[MIT](LICENSE) (c) 2026 Miguel Gomez
