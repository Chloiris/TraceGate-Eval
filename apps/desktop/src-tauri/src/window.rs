use tauri::{AppHandle, Emitter, Manager, Runtime, Window, WindowEvent};

use crate::state::DesktopState;

pub const MAIN_WINDOW_LABEL: &str = "main";
pub const CLOSE_REQUESTED_EVENT: &str = "tracegate-close-requested";

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum CloseDisposition {
    AskFrontend,
    Close,
}

fn close_disposition(is_quitting: bool) -> CloseDisposition {
    if is_quitting {
        CloseDisposition::Close
    } else {
        CloseDisposition::AskFrontend
    }
}

pub fn show_main_window<R: Runtime>(app: &AppHandle<R>) -> Result<(), String> {
    let window = app
        .get_webview_window(MAIN_WINDOW_LABEL)
        .ok_or_else(|| "main WebView window is unavailable".to_owned())?;
    window.show().map_err(|error| error.to_string())?;
    if window.is_minimized().unwrap_or(false) {
        window.unminimize().map_err(|error| error.to_string())?;
    }
    window.set_focus().map_err(|error| error.to_string())
}

pub fn hide_main_window<R: Runtime>(app: &AppHandle<R>) -> Result<(), String> {
    let window = app
        .get_webview_window(MAIN_WINDOW_LABEL)
        .ok_or_else(|| "main WebView window is unavailable".to_owned())?;
    window.hide().map_err(|error| error.to_string())
}

pub fn handle_window_event<R: Runtime>(window: &Window<R>, event: &WindowEvent) {
    if window.label() != MAIN_WINDOW_LABEL {
        return;
    }

    if let WindowEvent::CloseRequested { api, .. } = event {
        let state = window.state::<DesktopState>();
        if close_disposition(state.is_quitting()) == CloseDisposition::AskFrontend {
            api.prevent_close();
            let _ = window.emit(CLOSE_REQUESTED_EVENT, ());
        }
    }
}

#[cfg(test)]
mod tests {
    use super::{close_disposition, CloseDisposition};

    #[test]
    fn close_hides_until_an_explicit_quit_begins() {
        assert_eq!(close_disposition(false), CloseDisposition::AskFrontend);
        assert_eq!(close_disposition(true), CloseDisposition::Close);
    }
}
