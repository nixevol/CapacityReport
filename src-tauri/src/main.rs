#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::error::Error;
use std::fs;
use std::io::{Read, Write};
use std::net::{SocketAddr, TcpStream};
use std::path::{Path, PathBuf};
use std::sync::Mutex;
use std::thread;
use std::time::{Duration, Instant};

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
    let resource_path = app
        .path()
        .resolve(name, tauri::path::BaseDirectory::Resource)?;
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
    stop_existing_server_on_port(19082);

    let (mut rx, child) = app
        .shell()
        .sidecar("capareport-server")?
        .env(
            "CAPAREPORT_BASE_DIR",
            data_dir.to_string_lossy().to_string(),
        )
        .args(["--host", "127.0.0.1", "--port", "19082"])
        .spawn()?;

    if let Err(error) = wait_for_server("127.0.0.1:19082", Duration::from_secs(60)) {
        let _ = child.kill();
        return Err(error);
    }

    tauri::async_runtime::spawn(async move { while rx.recv().await.is_some() {} });

    let pid = child.pid();
    let state = app.state::<ServerState>();
    *state.0.lock().expect("server state lock poisoned") = Some(ServerProcess { child, pid });
    Ok(())
}

fn wait_for_server(addr: &str, timeout: Duration) -> Result<(), Box<dyn Error>> {
    let socket_addr: SocketAddr = addr.parse()?;
    let started_at = Instant::now();
    while started_at.elapsed() < timeout {
        if health_check(&socket_addr).unwrap_or(false) {
            return Ok(());
        }
        thread::sleep(Duration::from_millis(250));
    }
    Err(format!("Server did not start within {} seconds", timeout.as_secs()).into())
}

fn health_check(socket_addr: &SocketAddr) -> Result<bool, Box<dyn Error>> {
    let mut stream = TcpStream::connect_timeout(socket_addr, Duration::from_millis(500))?;
    stream.set_read_timeout(Some(Duration::from_millis(500)))?;
    stream.write_all(b"GET /health HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n")?;

    let mut response = String::new();
    stream.read_to_string(&mut response)?;
    Ok(response.starts_with("HTTP/1.1 200") || response.starts_with("HTTP/1.0 200"))
}

#[cfg(target_os = "windows")]
fn stop_existing_server_on_port(port: u16) {
    let Ok(output) = std::process::Command::new("netstat")
        .args(["-ano", "-p", "tcp"])
        .output()
    else {
        return;
    };

    let marker = format!(":{port}");
    let stdout = String::from_utf8_lossy(&output.stdout);
    for line in stdout.lines() {
        if !line.contains(&marker) || !line.to_ascii_uppercase().contains("LISTENING") {
            continue;
        }

        let Some(pid) = line.split_whitespace().last() else {
            continue;
        };
        if pid.parse::<u32>().is_err() {
            continue;
        }

        let _ = std::process::Command::new("taskkill")
            .args(["/F", "/T", "/PID", pid])
            .status();
    }
}

#[cfg(not(target_os = "windows"))]
fn stop_existing_server_on_port(_port: u16) {}

fn stop_server<R: Runtime>(app: &tauri::AppHandle<R>) {
    let state = app.state::<ServerState>();
    let child = state.0.lock().expect("server state lock poisoned").take();
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
