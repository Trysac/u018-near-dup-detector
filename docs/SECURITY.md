# Security notes

## Threat model

`trysac-near-dup-detector` is a pure library without I/O.

Defended:

- **Untrusted input**: arguments are validated; bad types, out-of-range values, non-UTF-8-encodable text, oversized documents, too many items or documents, and over-long ids raise `DedupError` with a code. The library never calls `eval`, `exec` or deserializes data.
- **Logging of content**: input text is never logged.
- **Process-dependent results**: the built-in `hash()` is never used, so fingerprints are reproducible across processes.

Not defended:

- **Resource use within limits**: a call can still use substantial memory and CPU up to the limits (100,000 documents, 1,000,000 characters per document, 10,000,000 items per fingerprint, `num_perm` up to 65536).
- **Adversarial collisions**: MinHash and SimHash are not cryptographic; an attacker can craft documents that collide or evade detection.
- **Supply chain**: a compromised dependency or CI action. Mitigation: no runtime dependencies, Dependabot weekly updates, actions pinned to major versions, minimal workflow permissions.
- **Leaked secrets**: tokens committed by mistake. Mitigation: `gitleaks` runs in the local gates and in CI; `.env` files are git-ignored.

## Publishing

Releases are published to PyPI with trusted publishing (OIDC) when available, never with a long-lived token stored in the repository.

To report a vulnerability, see [SECURITY.md](../SECURITY.md).
