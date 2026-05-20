use std::fs;
use std::path::{Path, PathBuf};
use std::sync::Mutex;
use std::error::Error;

use tauri::{Manager, Runtime};
use tauri_plugin_shell::process::CommandChild;
use tauri_plugin_shell::ShellExt;

struct ServerProcess {
    child: CommandChild,
    pid: u32,
}

struct ServerState(Mutex<Option<ServerProcess>>);

fn copy_resource<R: Runtime>(
    app: &tauri::App<R>,
    name: &str,
    data_dir: &Path,
) -> Result<(), Box<dyn Error>> {
    let target = data_dir.join(name);
    if target.exists() {
        return Ok(());
    }

    for source in resource_candidates(app, name)? {
        if source.exists() {
            fs::copy(source, target)?;
            return Ok(());
        }
    }

    Err(format!("Bundled resource not found: {name}").into())
}

fn resource_candidates<R: Runtime>(
    app: &tauri::App<R>,
    name: &str,
) -> Result<Vec<PathBuf>, Box<dyn Error>> {
    let resource_path = app.path().resolve(name, tauri::path::BaseDirectory::Resource)?;
    let escaped_parent_path = app
        .path()
        .resolve(format!("_up_/{name}"), tauri::path::BaseDirectory::Resource)?;
    let exe_dir = std::env::current_exe()?
        .parent()
        .map(Path::to_path_buf)
        .ok_or("Unable to resolve executable directory")?;

    Ok(vec![
        resource_path,
        escaped_parent_path,
        exe_dir.join(name),
        exe_dir.join("_up_").join(name),
    ])
}

fn start_server<R: Runtime>(app: &tauri::App<R>) -> Result<(), Box<dyn Error>> {
    let data_dir = app.path().app_data_dir()?;
    fs::create_dir_all(&data_dir)?;
    fs::create_dir_all(data_dir.join("cache"))?;
    fs::create_dir_all(data_dir.join("logs"))?;
    copy_resource(app, "Configure.json", &data_dir)?;
    copy_resource(app, "ReportScript.sql", &data_dir)?;

    let (mut rx, child) = app
        .shell()
        .sidecar("capareport-server")?
        .env("CAPAREPORT_BASE_DIR", data_dir.to_string_lossy().to_string())
        .args(["--host", "127.0.0.1", "--port", "19082"])
        .spawn()?;

    tauri::async_runtime::spawn(async move {
        while rx.recv().await.is_some() {}
    });

    let pid = child.pid();
    let state = app.state::<ServerState>();
    *state.0.lock().expect("server state lock poisoned") = Some(ServerProcess { child, pid });
    Ok(())
}

fn stop_server<R: Runtime>(app: &tauri::AppHandle<R>) {
    let state = app.state::<ServerState>();
    let child = state
        .0
        .lock()
        .expect("server state lock poisoned")
        .take();
    if let Some(process) = child {
        #[cfg(target_os = "windows")]
        {
            let _ = std::process::Command::new("taskkill")
                .args(["/F", "/T", "/PID", &process.pid.to_string()])
                .status();
        }
        let _ = process.child.kill();
    }
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(ServerState(Mutex::new(None)))
        .setup(|app| {
            start_server(app)?;
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                stop_server(window.app_handle());
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
