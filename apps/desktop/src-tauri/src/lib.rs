mod commands;
mod deep_link;
mod lifecycle;
mod platform;
mod sidecar;
mod state;
mod tray;
mod window;

use tauri::Manager;

use state::DesktopState;

pub fn run() {
    let app = tauri::Builder::default()
        // Tauri requires the single-instance plugin to be registered first.
        .plugin(tauri_plugin_single_instance::init(
            |app, arguments, _cwd| {
                if !deep_link::deliver_from_arguments(app, arguments.iter().map(String::as_str)) {
                    let _ = window::show_main_window(app);
                }
            },
        ))
        .plugin(tauri_plugin_deep_link::init())
        .plugin(tauri_plugin_shell::init())
        .manage(DesktopState::default())
        .invoke_handler(tauri::generate_handler![
            commands::get_desktop_status,
            commands::get_api_connection,
            commands::take_pending_deep_link,
            commands::show_main_window,
            commands::quit_tracegate,
        ])
        .on_window_event(window::handle_window_event)
        .on_menu_event(tray::handle_menu_event)
        .on_tray_icon_event(tray::handle_tray_icon_event)
        .setup(|app| {
            #[cfg(all(debug_assertions, windows))]
            {
                use tauri_plugin_deep_link::DeepLinkExt;
                app.deep_link().register_all()?;
            }

            tray::build(app)?;

            let state = app.state::<DesktopState>();
            state.sidecar.start(app.handle().clone());

            let _ = deep_link::deliver_from_arguments(app.handle(), std::env::args().skip(1));
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("failed to build TraceGate Studio desktop shell");

    app.run(|app_handle, event| lifecycle::handle_run_event(app_handle, &event));
}
