use tauri_plugin_shell::ShellExt;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            // Spawn the Python FastAPI backend as a sidecar
            let shell = app.shell();
            let _child = shell
                .sidecar("api_server")
                .expect("failed to find api_server sidecar")
                .spawn()
                .expect("failed to spawn api_server");
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
