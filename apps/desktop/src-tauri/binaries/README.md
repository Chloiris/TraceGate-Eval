# Native Sidecars

This directory intentionally contains no fake backend executable. A platform
build must stage exactly one real PyInstaller output with the matching helper
script:

- `tracegate-backend-aarch64-apple-darwin`
- `tracegate-backend-x86_64-pc-windows-msvc.exe`

Tauri's `externalBin` resolution fails the build when the required target
binary is missing. That failure is intentional and must not be bypassed by
renaming an artifact produced on another operating system.
