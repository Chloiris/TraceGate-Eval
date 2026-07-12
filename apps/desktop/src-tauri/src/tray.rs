use serde::Serialize;
use tauri::{
    menu::{Menu, MenuEvent, MenuItem, PredefinedMenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    App, AppHandle, Emitter, Runtime,
};

use crate::{lifecycle, window};

pub const TRAY_ID: &str = "tracegate-main";
pub const TRAY_ACTION_EVENT: &str = "tracegate-tray-action";

const OPEN: &str = "open";
const SCAN_ALL: &str = "scan-all";
const PAUSE: &str = "pause-monitoring";
const RESUME: &str = "resume-monitoring";
const RECENT_PULL_REQUESTS: &str = "recent-pull-requests";
const HIGH_RISK: &str = "high-risk-pull-requests";
const SETTINGS: &str = "settings";
const LOGS: &str = "logs";
const DIAGNOSTICS: &str = "diagnostics";
const QUIT: &str = "quit";

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum TrayAction {
    ScanAll,
    PauseMonitoring,
    ResumeMonitoring,
    RecentPullRequests,
    HighRiskPullRequests,
    Settings,
    Logs,
    Diagnostics,
}

impl TrayAction {
    fn from_menu_id(id: &str) -> Option<Self> {
        match id {
            SCAN_ALL => Some(Self::ScanAll),
            PAUSE => Some(Self::PauseMonitoring),
            RESUME => Some(Self::ResumeMonitoring),
            RECENT_PULL_REQUESTS => Some(Self::RecentPullRequests),
            HIGH_RISK => Some(Self::HighRiskPullRequests),
            SETTINGS => Some(Self::Settings),
            LOGS => Some(Self::Logs),
            DIAGNOSTICS => Some(Self::Diagnostics),
            _ => None,
        }
    }

    fn opens_window(self) -> bool {
        matches!(
            self,
            Self::RecentPullRequests
                | Self::HighRiskPullRequests
                | Self::Settings
                | Self::Logs
                | Self::Diagnostics
        )
    }
}

pub fn build<R: Runtime>(app: &App<R>) -> Result<(), Box<dyn std::error::Error>> {
    let open = MenuItem::with_id(app, OPEN, "Open TraceGate", true, None::<&str>)?;
    let scan_all = MenuItem::with_id(app, SCAN_ALL, "Scan All Repositories", true, None::<&str>)?;
    let pause = MenuItem::with_id(app, PAUSE, "Pause Monitoring", true, None::<&str>)?;
    let resume = MenuItem::with_id(app, RESUME, "Resume Monitoring", true, None::<&str>)?;
    let recent = MenuItem::with_id(
        app,
        RECENT_PULL_REQUESTS,
        "Recent Pull Requests",
        true,
        None::<&str>,
    )?;
    let high_risk = MenuItem::with_id(
        app,
        HIGH_RISK,
        "View High-Risk Pull Requests",
        true,
        None::<&str>,
    )?;
    let settings = MenuItem::with_id(app, SETTINGS, "Settings", true, None::<&str>)?;
    let logs = MenuItem::with_id(app, LOGS, "View Logs", true, None::<&str>)?;
    let diagnostics = MenuItem::with_id(app, DIAGNOSTICS, "Diagnostics", true, None::<&str>)?;
    let quit = MenuItem::with_id(app, QUIT, "Quit TraceGate", true, None::<&str>)?;
    let separator_one = PredefinedMenuItem::separator(app)?;
    let separator_two = PredefinedMenuItem::separator(app)?;
    let separator_three = PredefinedMenuItem::separator(app)?;

    let menu = Menu::with_items(
        app,
        &[
            &open,
            &separator_one,
            &scan_all,
            &pause,
            &resume,
            &recent,
            &high_risk,
            &separator_two,
            &settings,
            &logs,
            &diagnostics,
            &separator_three,
            &quit,
        ],
    )?;

    let icon = app.default_window_icon().cloned().ok_or_else(|| {
        std::io::Error::new(
            std::io::ErrorKind::NotFound,
            "default window icon is missing",
        )
    })?;

    TrayIconBuilder::with_id(TRAY_ID)
        .tooltip("TraceGate Studio")
        .icon(icon)
        .icon_as_template(cfg!(target_os = "macos"))
        .menu(&menu)
        .show_menu_on_left_click(false)
        .build(app)?;

    Ok(())
}

pub fn handle_menu_event<R: Runtime>(app: &AppHandle<R>, event: MenuEvent) {
    if event.id() == OPEN {
        let _ = window::show_main_window(app);
        return;
    }
    if event.id() == QUIT {
        lifecycle::request_exit(app);
        return;
    }

    if let Some(action) = TrayAction::from_menu_id(event.id().as_ref()) {
        let _ = app.emit(TRAY_ACTION_EVENT, action);
        if action.opens_window() {
            let _ = window::show_main_window(app);
        }
    }
}

pub fn handle_tray_icon_event<R: Runtime>(app: &AppHandle<R>, event: TrayIconEvent) {
    if let TrayIconEvent::Click {
        id,
        button: MouseButton::Left,
        button_state: MouseButtonState::Up,
        ..
    } = event
    {
        if id == TRAY_ID {
            let _ = window::show_main_window(app);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::{TrayAction, DIAGNOSTICS, PAUSE, QUIT};

    #[test]
    fn only_known_menu_items_become_frontend_actions() {
        assert_eq!(
            TrayAction::from_menu_id(PAUSE),
            Some(TrayAction::PauseMonitoring)
        );
        assert_eq!(
            TrayAction::from_menu_id(DIAGNOSTICS),
            Some(TrayAction::Diagnostics)
        );
        assert_eq!(TrayAction::from_menu_id(QUIT), None);
        assert_eq!(TrayAction::from_menu_id("unknown"), None);
    }
}
