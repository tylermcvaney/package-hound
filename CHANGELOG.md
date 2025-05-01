# Changelog
## v1.0.1 - 2025-04-30
### Added
- Added new test cases for metadata file handling scenarios
  - More comprehensive test coverage for Maven metadata files at various levels
  - Added test cases for NPM package paths ending with package.json

### Fixed
- Updated `_extract_package_name` to handle Maven metadata files more robustly
- Ensured proper extraction of artifact_id and group_id even for edge cases
- Improved metadata file handling for Maven and NPM packages

## v1.0.0
### Added
- Initial release of the Artifactory Package Checker
- Support for checking package existence across multiple repository types:
  - Python (PyPI)
  - NPM
  - Maven
  - NuGet
  - Terraform
  - Docker
- Multi-threaded package checking for improved performance
- Automatic repository mapping detection
- CSV input and output for batch processing
- Comprehensive logging with configurable verbosity
- Detailed error reporting for packages not found
- Added test coverage with mock objects
- Support for self-signed SSL certificates with `--cert-path` option
- Option to disable SSL verification with `--no-ssl-verify` (for testing only)