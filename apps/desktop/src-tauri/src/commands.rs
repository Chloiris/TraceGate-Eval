use tauri::{AppHandle, State};

use crate::{
    credentials::{self, CredentialKind, CredentialStatus},
    deep_link::DeepLinkRoute,
    lifecycle,
    sidecar::ApiConnection,
    state::{DesktopState, DesktopStatus},
    window,
};

#[tauri::command]
pub fn get_credential_status(kind: CredentialKind) -> Result<CredentialStatus, String> {
    credentials::credential_status(kind).map_err(|error| error.to_string())
}

#[tauri::command]
pub fn store_credential(kind: CredentialKind, secret: String) -> Result<CredentialStatus, String> {
    credentials::store_credential(kind, &secret).map_err(|error| error.to_string())
}

#[tauri::command]
pub fn delete_credential(kind: CredentialKind) -> Result<CredentialStatus, String> {
    credentials::delete_credential(kind).map_err(|error| error.to_string())
}

#[tauri::command]
pub fn get_desktop_status(state: State<'_, DesktopState>) -> DesktopStatus {
    state.snapshot()
}

#[tauri::command]
pub fn get_api_connection(state: State<'_, DesktopState>) -> Result<ApiConnection, String> {
    state
        .sidecar
        .api_connection()
        .ok_or_else(|| "TraceGate backend is not healthy; API connection is unavailable".to_owned())
}

#[tauri::command]
pub fn take_pending_deep_link(state: State<'_, DesktopState>) -> Option<DeepLinkRoute> {
    state.take_pending_deep_link()
}

#[tauri::command]
pub fn show_main_window(app: AppHandle) -> Result<(), String> {
    window::show_main_window(&app)
}

#[tauri::command]
pub fn quit_tracegate(app: AppHandle) {
    lifecycle::request_exit(&app);
}
