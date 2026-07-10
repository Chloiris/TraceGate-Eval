use tauri::{AppHandle, Manager, RunEvent, Runtime};

use crate::{deep_link, state::DesktopState, window};

pub fn request_exit<R: Runtime>(app: &AppHandle<R>) {
    let state = app.state::<DesktopState>();
    state.begin_quit();
    state.sidecar.shutdown(app);
    app.exit(0);
}

pub fn handle_run_event<R: Runtime>(app: &AppHandle<R>, event: &RunEvent) {
    match event {
        RunEvent::Exit => {
            let state = app.state::<DesktopState>();
            state.begin_quit();
            state.sidecar.shutdown(app);
        }
        RunEvent::ExitRequested { .. } => {
            let state = app.state::<DesktopState>();
            state.begin_quit();
            state.sidecar.shutdown(app);
        }
        #[cfg(target_os = "macos")]
        RunEvent::Opened { urls } => {
            for url in urls {
                if let Ok(route) = deep_link::parse(url.as_str()) {
                    deep_link::deliver(app, route);
                    break;
                }
            }
        }
        #[cfg(target_os = "macos")]
        RunEvent::Reopen { .. } => {
            let _ = window::show_main_window(app);
        }
        _ => {}
    }
}
