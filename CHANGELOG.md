# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

### Changed

### Removed

### Fixed

## [0.1.2] - 2025-09-26

### Added
- Structured logging system with configurable log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Centralized logging setup in taf/core/logging.py
- Python-dotenv support for loading .env files in webhook server
- .env.example file with sample environment variables
- Logging throughout TAF core, Maestro, and Memora clients

### Changed
- Made TAFConfig fields required for better validation
- Replaced print statements with proper logging in webhook server
- Updated all tests to work with required configuration fields

### Fixed
- Type annotation for log_level configuration (changed from Optional[str] to str)
- Removed unused Optional import from typing

## [0.1.1] - 2025-09-25

### Added
- Environment variable support for TAF configuration
- Support for memora_auth_token, memora_base_url, maestro_base_url, and twilio_account_sid

### Changed
- Updated webhook_server.py to use environment variables instead of hardcoded configuration
- Simplified webhook handler by removing unnecessary TAF null check
- Modernized Pydantic usage in tests (dict() → model_dump(), schema() → model_json_schema())

### Removed
- Debug logging statements from maestro.py and memora.py API clients

### Fixed
- Updated test suite to match actual TAFConfig field names
- Fixed deprecated Pydantic v1 method usage in tests

## [0.1.0] - 2025-09-17

### Added
- Initial release of Twilio Agentic Framework
- Basic `hello()` function for package validation
- Full development environment setup with Poetry
- Type checking support with mypy and py.typed marker
- Code quality tools: black, isort, pytest
- Pre-commit hooks for automated code quality
- Buildkite CI/CD pipeline
- MIT License
- Comprehensive test suite
- Documentation and examples

[Unreleased]: https://github.com/twilio-internal/twilio-agentic-framework-python/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/twilio-internal/twilio-agentic-framework-python/releases/tag/v0.1.0