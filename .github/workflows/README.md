# CLI Release Workflows

This directory contains GitHub Actions workflows for building and releasing the Genkit CLI.

## Current Workflows (Unsigned)

### `build-cli-binaries.yml` - Build CLI Binaries (RC)
- **Purpose**: Build and release unsigned CLI binaries
- **Trigger**: Manual workflow dispatch
- **Inputs**:
  - `version`: Version tag to build (e.g., `v1.0.0`, `v1.0.0-rc.1`)
  - `create_rc`: Create release candidate with unsigned binaries (optional, default: false)
- **Outputs**: 
  - Binary artifacts for all platforms (Linux x64/ARM64, macOS x64/ARM64, Windows x64)
  - Optional: GitHub release with unsigned binaries for testing

### `promote-cli-release.yml` - Promote CLI Release (Unsigned)
- **Purpose**: Promote RC releases to final releases
- **Trigger**: Manual workflow dispatch
- **Inputs**:
  - `rc_version`: RC version to promote (e.g., `v1.0.0-rc.1`)
  - `final_version`: Final version tag (e.g., `v1.0.0`)
- **Outputs**: Final GitHub release with unsigned binaries

## Preserved Workflows (Signed - Disabled)

### `build-cli-binaries-signed.yml` - Build CLI Binaries (SIGNED - DISABLED)
- **Purpose**: Preserved for future code signing implementation
- **Status**: Disabled - shows error message directing users to unsigned workflow
- **Future**: Will be re-enabled when code signing is implemented

### `promote-cli-release-signed.yml` - Promote CLI Release (SIGNED - DISABLED)
- **Purpose**: Preserved for future code signing implementation
- **Status**: Disabled - shows error message directing users to unsigned workflow
- **Future**: Will be re-enabled when code signing is implemented

## Usage

### For RC Releases:
1. Run "Build CLI Binaries (RC)" workflow
2. Set version (e.g., `v1.0.0-rc.1`)
3. Check "Create release" to publish RC with unsigned binaries

### For Final Releases:
1. Run "Promote CLI Release (Unsigned)" workflow
2. Set RC version (e.g., `v1.0.0-rc.1`)
3. Set final version (e.g., `v1.0.0`)

## Binary Naming Convention

The workflows generate binaries with the following naming convention:
- `genkit-linux-x64` - Linux x64
- `genkit-linux-arm64` - Linux ARM64
- `genkit-darwin-x64` - macOS x64 (Intel)
- `genkit-darwin-arm64` - macOS ARM64 (Apple Silicon)
- `genkit-win32-x64.exe` - Windows x64

## Future Code Signing

When code signing is implemented:
1. Rename workflows back to original names
2. Re-enable signed workflows
3. Update install script to use signed binaries
4. Update binary naming to include `-signed` suffix

## Installation Script

The `bin/install_cli` script has been updated to work with unsigned releases. It downloads the latest non-prerelease binaries from GitHub releases.

## Notes

- All current releases use unsigned binaries
- The install script (`genkit.tools`) works with unsigned binaries
- When code signing is ready, the signed workflows will be re-enabled
- The disabled workflows prevent accidental use of incomplete signing processes 