use super::WINDOWS_X64_SIDECAR;

pub fn platform_name() -> &'static str {
    "windows-x86_64"
}

pub fn sidecar_binary_name() -> Option<&'static str> {
    Some(WINDOWS_X64_SIDECAR)
}
