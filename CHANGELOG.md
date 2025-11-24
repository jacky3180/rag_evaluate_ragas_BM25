# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- GitHub-ready open-source assets: `LICENSE`, `CODE_OF_CONDUCT.md`,
  `CONTRIBUTING.md`, `SECURITY.md`, `CHANGELOG.md`, and `.gitignore`.
- Repository hygiene updates to support public release workflows.

### Changed
- Updated `README.md` references to point contributors toward the new
  governance and contribution documents.

### Security
- Documented the initial security policy and disclosure process.

## [1.0.0] - 2025-10-28
### Added
- Stable `ContextEntityRecall` implementation to eliminate LLM JSON parsing
  failures.
- Hybrid evaluation workflow combining Ragas v0.3.2 and BM25-based metrics.
- FastAPI Web UI with caching, database persistence, and rich history analysis.

### Performance
- Performance-optimized release featuring API caching, database indexing, batch
  processing, and reduced logging overhead. Overall throughput improved by
  approximately 70%.

### Documentation
- Comprehensive README covering features, architecture, deployment, and data
  requirements.
- Detailed optimization guides (`PERFORMANCE_OPTIMIZATION.md`,
  `PERFORMANCE_QUICKSTART.md`, etc.).

[Unreleased]: https://github.com/your-org/your-repo/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/your-org/your-repo/releases/tag/v1.0.0

