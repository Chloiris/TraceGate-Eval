use super::MACOS_ARM64_SIDECAR;

pub fn platform_name() -> &'static str {
    "macos-aarch64"
}

pub fn sidecar_binary_name() -> Option<&'static str> {
    Some(MACOS_ARM64_SIDECAR)
}
