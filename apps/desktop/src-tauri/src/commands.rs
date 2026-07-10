use tauri::{AppHandle, State};
use tauri_plugin_autostart::ManagerExt;
use tauri_plugin_notification::NotificationExt;

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
pub fn get_autostart_enabled(app: AppHandle) -> Result<bool, String> {
    app.autolaunch()
        .is_enabled()
        .map_err(|error| format!("could not read autostart state: {error}"))
}

#[tauri::command]
pub fn set_autostart_enabled(app: AppHandle, enabled: bool) -> Result<bool, String> {
    let manager = app.autolaunch();
    if enabled {
        manager.enable()
    } else {
        manager.disable()
    }
    .map_err(|error| format!("could not update autostart state: {error}"))?;

    manager
        .is_enabled()
        .map_err(|error| format!("could not verify autostart state: {error}"))
}

#[tauri::command]
pub fn show_review_notification(app: AppHandle, title: String, body: String) -> Result<(), String> {
    validate_notification_text("title", &title, 96)?;
    validate_notification_text("body", &body, 512)?;
    app.notification()
        .builder()
        .title(title)
        .body(body)
        .show()
        .map_err(|error| format!("could not show notification: {error}"))
}

#[tauri::command]
pub fn quit_tracegate(app: AppHandle) {
    lifecycle::request_exit(&app);
}

fn validate_notification_text(field: &str, value: &str, max_chars: usize) -> Result<(), String> {
    let value = value.trim();
    if value.is_empty() {
        return Err(format!("notification {field} must not be empty"));
    }
    if value.chars().count() > max_chars {
        return Err(format!(
            "notification {field} exceeds {max_chars} characters"
        ));
    }
    if value
        .chars()
        .any(|character| character.is_control() && character != '\n')
    {
        return Err(format!("notification {field} contains control characters"));
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::validate_notification_text;

    #[test]
    fn notification_text_is_bounded_and_non_empty() {
        assert!(validate_notification_text("title", "TraceGate", 96).is_ok());
        assert!(validate_notification_text("title", "  ", 96).is_err());
        assert!(validate_notification_text("title", &"x".repeat(97), 96).is_err());
        assert!(validate_notification_text("body", "safe\nmessage", 512).is_ok());
        assert!(validate_notification_text("body", "unsafe\u{0}", 512).is_err());
    }
}
