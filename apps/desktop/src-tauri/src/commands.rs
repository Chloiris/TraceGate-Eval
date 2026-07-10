use tauri::{AppHandle, State};
use tauri_plugin_autostart::ManagerExt;
use tauri_plugin_notification::{NotificationExt, PermissionState};
use tauri_plugin_shell::ShellExt;

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
pub fn hide_main_window(app: AppHandle) -> Result<(), String> {
    window::hide_main_window(&app)
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
pub fn show_review_notification(
    app: AppHandle,
    title: String,
    body: String,
    deep_link: Option<String>,
) -> Result<(), String> {
    show_actionable_notification(app, title, body, deep_link)
}

pub fn show_actionable_notification<R: tauri::Runtime>(
    app: AppHandle<R>,
    title: String,
    body: String,
    deep_link: Option<String>,
) -> Result<(), String> {
    validate_notification_text("title", &title, 96)?;
    validate_notification_text("body", &body, 512)?;
    let route = deep_link
        .map(|raw| {
            crate::deep_link::parse(&raw)
                .map_err(|error| format!("notification deep link is invalid: {error}"))
        })
        .transpose()?;
    let mut permission = app
        .notification()
        .permission_state()
        .map_err(|error| format!("could not read notification permission: {error}"))?;
    if matches!(
        permission,
        PermissionState::Prompt | PermissionState::PromptWithRationale
    ) {
        permission = app
            .notification()
            .request_permission()
            .map_err(|error| format!("could not request notification permission: {error}"))?;
    }
    if permission != PermissionState::Granted {
        return Err(format!("notification permission is {permission}"));
    }

    #[cfg(target_os = "macos")]
    {
        let application = if tauri::is_dev() {
            "com.apple.Terminal"
        } else {
            &app.config().identifier
        };
        let _ = notify_rust::set_application(application);
    }
    let mut notification = notify_rust::Notification::new();
    notification.summary(&title).body(&body);
    #[cfg(windows)]
    notification.app_id(&app.config().identifier);
    let handle = notification
        .show()
        .map_err(|error| format!("could not show actionable notification: {error}"))?;
    std::thread::spawn(move || {
        handle.wait_for_action(move |action| {
            if notification_action_opens(action) {
                if let Some(route) = route {
                    crate::deep_link::deliver(&app, route);
                } else {
                    let _ = crate::window::show_main_window(&app);
                }
            }
        });
    });
    Ok(())
}

#[tauri::command]
#[allow(deprecated)]
pub fn open_workspace(app: AppHandle, path: String, editor: bool) -> Result<(), String> {
    let canonical = validate_workspace_path(&path)?;
    let target = if editor {
        let file_url = tauri::Url::from_file_path(&canonical)
            .map_err(|_| "workspace path could not be converted to a file URL".to_owned())?;
        file_url.as_str().replacen("file://", "vscode://file", 1)
    } else {
        canonical.to_string_lossy().into_owned()
    };
    app.shell()
        .open(target, None)
        .map_err(|error| format!("could not open workspace: {error}"))
}

#[tauri::command]
#[allow(deprecated)]
pub fn open_workspace_file(
    app: AppHandle,
    workspace: String,
    path: String,
    line: Option<u32>,
) -> Result<(), String> {
    let root = validate_workspace_path(&workspace)?;
    let file = validate_workspace_file(&root, &path)?;
    if matches!(line, Some(0)) {
        return Err("workspace file line must be positive".to_owned());
    }
    let file_url = tauri::Url::from_file_path(&file)
        .map_err(|_| "workspace file could not be converted to a file URL".to_owned())?;
    let mut target = file_url.as_str().replacen("file://", "vscode://file", 1);
    if let Some(line) = line {
        target.push(':');
        target.push_str(&line.to_string());
    }
    app.shell()
        .open(target, None)
        .map_err(|error| format!("could not open workspace file: {error}"))
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

fn validate_workspace_path(path: &str) -> Result<std::path::PathBuf, String> {
    if path.trim() != path || path.is_empty() || path.len() > 4096 || path.contains('\0') {
        return Err("workspace path is invalid".to_owned());
    }
    let candidate = std::path::PathBuf::from(path);
    if !candidate.is_absolute() {
        return Err("workspace path must be absolute".to_owned());
    }
    let canonical = candidate
        .canonicalize()
        .map_err(|_| "workspace path does not exist".to_owned())?;
    if !canonical.is_dir() {
        return Err("workspace path must be a directory".to_owned());
    }
    let sensitive = [".ssh", ".aws", ".azure", ".kube", "gcloud"];
    if canonical.components().any(|component| {
        let value = component.as_os_str().to_string_lossy();
        sensitive
            .iter()
            .any(|blocked| value.eq_ignore_ascii_case(blocked))
    }) {
        return Err("sensitive credential directories cannot be opened as workspaces".to_owned());
    }
    Ok(canonical)
}

fn validate_workspace_file(
    root: &std::path::Path,
    path: &str,
) -> Result<std::path::PathBuf, String> {
    if path.trim() != path || path.is_empty() || path.len() > 2048 || path.contains('\0') {
        return Err("workspace file path is invalid".to_owned());
    }
    let relative = std::path::Path::new(path);
    if relative.is_absolute()
        || relative.components().any(|component| {
            matches!(
                component,
                std::path::Component::ParentDir
                    | std::path::Component::RootDir
                    | std::path::Component::Prefix(_)
            )
        })
    {
        return Err("workspace file path must stay relative to the workspace".to_owned());
    }
    let canonical = root
        .join(relative)
        .canonicalize()
        .map_err(|_| "workspace file does not exist".to_owned())?;
    if !canonical.starts_with(root) || !canonical.is_file() {
        return Err("workspace file must remain inside the workspace".to_owned());
    }
    Ok(canonical)
}

fn notification_action_opens(action: &str) -> bool {
    action == "default" || action == "open"
}

#[cfg(test)]
mod tests {
    use super::{
        notification_action_opens, validate_notification_text, validate_workspace_file,
        validate_workspace_path,
    };

    #[test]
    fn notification_text_is_bounded_and_non_empty() {
        assert!(validate_notification_text("title", "TraceGate", 96).is_ok());
        assert!(validate_notification_text("title", "  ", 96).is_err());
        assert!(validate_notification_text("title", &"x".repeat(97), 96).is_err());
        assert!(validate_notification_text("body", "safe\nmessage", 512).is_ok());
        assert!(validate_notification_text("body", "unsafe\u{0}", 512).is_err());
    }

    #[test]
    fn workspace_opening_requires_an_existing_absolute_directory() {
        let manifest = env!("CARGO_MANIFEST_DIR");
        assert!(validate_workspace_path(manifest).is_ok());
        assert!(validate_workspace_path("relative/path").is_err());
        assert!(validate_workspace_path(" /tmp").is_err());
    }

    #[test]
    fn workspace_file_opening_rejects_traversal_and_accepts_real_files() {
        let root = validate_workspace_path(env!("CARGO_MANIFEST_DIR")).expect("manifest root");
        assert!(validate_workspace_file(&root, "Cargo.toml").is_ok());
        assert!(validate_workspace_file(&root, "../Cargo.toml").is_err());
        assert!(validate_workspace_file(&root, "/tmp/file").is_err());
    }

    #[test]
    fn only_notification_activation_opens_the_staged_route() {
        assert!(notification_action_opens("default"));
        assert!(notification_action_opens("open"));
        assert!(!notification_action_opens("__closed"));
        assert!(!notification_action_opens("dismiss"));
    }
}
