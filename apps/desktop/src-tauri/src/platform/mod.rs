#[cfg(any(test, all(target_os = "macos", target_arch = "aarch64")))]
pub const MACOS_ARM64_SIDECAR: &str = "tracegate-backend-aarch64-apple-darwin";
#[cfg(any(test, all(target_os = "windows", target_arch = "x86_64")))]
pub const WINDOWS_X64_SIDECAR: &str = "tracegate-backend-x86_64-pc-windows-msvc.exe";

#[cfg(all(target_os = "macos", target_arch = "aarch64"))]
mod macos;
#[cfg(not(any(
    all(target_os = "macos", target_arch = "aarch64"),
    all(target_os = "windows", target_arch = "x86_64")
)))]
mod unsupported;
#[cfg(all(target_os = "windows", target_arch = "x86_64"))]
mod windows;

#[cfg(all(target_os = "macos", target_arch = "aarch64"))]
pub use macos::{platform_name, sidecar_binary_name};
#[cfg(not(any(
    all(target_os = "macos", target_arch = "aarch64"),
    all(target_os = "windows", target_arch = "x86_64")
)))]
pub use unsupported::{platform_name, sidecar_binary_name};
#[cfg(all(target_os = "windows", target_arch = "x86_64"))]
pub use windows::{platform_name, sidecar_binary_name};

#[cfg(test)]
mod tests {
    use super::{MACOS_ARM64_SIDECAR, WINDOWS_X64_SIDECAR};

    #[test]
    fn sidecar_names_match_tauri_target_triples_exactly() {
        assert_eq!(
            MACOS_ARM64_SIDECAR,
            "tracegate-backend-aarch64-apple-darwin"
        );
        assert_eq!(
            WINDOWS_X64_SIDECAR,
            "tracegate-backend-x86_64-pc-windows-msvc.exe"
        );
        assert!(!MACOS_ARM64_SIDECAR.ends_with(".exe"));
        assert!(WINDOWS_X64_SIDECAR.ends_with(".exe"));
    }
}
