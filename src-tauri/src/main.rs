#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::error::Error;
use std::fs;
use std::io::{Read, Write};
use std::net::{SocketAddr, TcpStream};
use std::path::{Path, PathBuf};
use std::sync::Mutex;
use std::thread;
use std::time::{Duration, Instant};

use sysinfo::{Pid, ProcessesToUpdate, Signal, System};
use tauri::{Manager, Runtime};
use tauri_plugin_dialog::DialogExt;
use tauri_plugin_shell::process::CommandChild;
use tauri_plugin_shell::ShellExt;

const SERVER_PORT: u16 = 9081;
const SERVER_ADDR: &str = "127.0.0.1:9081";
const HTTP_ERROR_PREFIX: &str = "CAPAREPORT_HTTP_ERROR:";
const SERVER_PROCESS_NAME: &str = "capareport-server";
const SERVER_PID_FILE: &str = "server.pid";

struct ServerProcess {
    child: CommandChild,
    pid_file: PathBuf,
}

struct ServerState(Mutex<Option<ServerProcess>>);

#[derive(serde::Deserialize)]
struct DownloadHeader {
    name: String,
    value: String,
}

#[derive(serde::Deserialize)]
struct DownloadFileRequest {
    url: String,
    method: String,
    filename: String,
    headers: Vec<DownloadHeader>,
    body: Option<String>,
}

#[derive(serde::Serialize)]
struct DownloadFileResult {
    saved: bool,
    path: Option<String>,
}

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
    let pid_file = data_dir.join(SERVER_PID_FILE);
    stop_recorded_server(&pid_file);
    ensure_server_port_available(SERVER_ADDR)?;

    let port_arg = SERVER_PORT.to_string();
    let (mut rx, child) = app
        .shell()
        .sidecar("capareport-server")?
        .env(
            "CAPAREPORT_BASE_DIR",
            data_dir.to_string_lossy().to_string(),
        )
        .args(["--host", "127.0.0.1", "--port", &port_arg])
        .spawn()?;
    let pid = child.pid();
    fs::write(&pid_file, pid.to_string())?;

    if let Err(error) = wait_for_server(SERVER_ADDR, Duration::from_secs(60)) {
        let _ = child.kill();
        let _ = fs::remove_file(&pid_file);
        return Err(error);
    }

    tauri::async_runtime::spawn(async move { while rx.recv().await.is_some() {} });

    let state = app.state::<ServerState>();
    *state.0.lock().expect("server state lock poisoned") = Some(ServerProcess { child, pid_file });
    Ok(())
}

fn ensure_server_port_available(addr: &str) -> Result<(), Box<dyn Error>> {
    let socket_addr: SocketAddr = addr.parse()?;
    if TcpStream::connect_timeout(&socket_addr, Duration::from_millis(300)).is_ok() {
        return Err(format!("Port {SERVER_PORT} is already in use").into());
    }
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

fn stop_recorded_server(pid_file: &Path) {
    let Ok(content) = fs::read_to_string(pid_file) else {
        return;
    };

    if let Ok(pid) = content.trim().parse::<u32>() {
        if !terminate_server_process(pid) {
            let _ = fs::remove_file(pid_file);
            return;
        }
        wait_for_process_exit(pid, Duration::from_secs(5));
    }
    let _ = fs::remove_file(pid_file);
}

fn terminate_server_process(pid: u32) -> bool {
    let mut system = System::new();
    let pid = Pid::from_u32(pid);
    system.refresh_processes(ProcessesToUpdate::Some(&[pid]), true);

    let Some(process) = system.process(pid) else {
        return false;
    };

    if !is_server_process_name(process.name()) {
        return false;
    }

    if process.kill_with(Signal::Kill) != Some(true) {
        let _ = process.kill();
    }
    true
}

fn wait_for_process_exit(pid: u32, timeout: Duration) {
    let started_at = Instant::now();
    while started_at.elapsed() < timeout {
        if !is_process_running(pid) {
            return;
        }
        thread::sleep(Duration::from_millis(100));
    }
}

fn is_process_running(pid: u32) -> bool {
    let mut system = System::new();
    let pid = Pid::from_u32(pid);
    system.refresh_processes(ProcessesToUpdate::Some(&[pid]), true);
    system.process(pid).is_some()
}

fn is_server_process_name(name: &std::ffi::OsStr) -> bool {
    let normalized = name.to_string_lossy().to_ascii_lowercase();
    normalized == SERVER_PROCESS_NAME || normalized == format!("{SERVER_PROCESS_NAME}.exe")
}

fn stop_server<R: Runtime>(app: &tauri::AppHandle<R>) {
    let state = app.state::<ServerState>();
    let child = state.0.lock().expect("server state lock poisoned").take();
    if let Some(process) = child {
        let _ = process.child.kill();
        let _ = fs::remove_file(process.pid_file);
    }
}

#[tauri::command]
async fn download_to_file(
    app: tauri::AppHandle,
    window: tauri::Window,
    request: DownloadFileRequest,
) -> Result<DownloadFileResult, String> {
    let filename = safe_download_filename(&request.filename);
    let mut dialog = app
        .dialog()
        .file()
        .set_file_name(&filename)
        .set_parent(&window);

    if let Some(extension) = Path::new(&filename)
        .extension()
        .and_then(|value| value.to_str())
        .filter(|value| !value.is_empty())
    {
        dialog = dialog.add_filter(extension.to_ascii_uppercase(), &[extension]);
    }

    let Some(file_path) = dialog
        .blocking_save_file()
        .map(|file_path| file_path.into_path().map_err(|error| error.to_string()))
        .transpose()?
    else {
        return Ok(DownloadFileResult {
            saved: false,
            path: None,
        });
    };

    if let Err(error) = write_download(request, &file_path).await {
        let _ = fs::remove_file(&file_path);
        return Err(error);
    }

    Ok(DownloadFileResult {
        saved: true,
        path: Some(file_path.to_string_lossy().to_string()),
    })
}

#[tauri::command]
fn open_path_in_file_manager(path: String) -> Result<(), String> {
    let target = PathBuf::from(path);
    let directory = if target.is_dir() {
        target
    } else {
        target
            .parent()
            .map(Path::to_path_buf)
            .ok_or_else(|| "Unable to resolve download directory".to_string())?
    };

    open::that(directory).map_err(|error| format!("Unable to open download directory: {error}"))
}

async fn write_download(request: DownloadFileRequest, file_path: &Path) -> Result<(), String> {
    let method = reqwest::Method::from_bytes(request.method.as_bytes())
        .map_err(|error| format!("Invalid download method: {error}"))?;
    let client = reqwest::Client::new();
    let mut builder = client.request(method, request.url);

    for header in request.headers {
        let name = reqwest::header::HeaderName::from_bytes(header.name.as_bytes())
            .map_err(|error| format!("Invalid download header: {error}"))?;
        let value = reqwest::header::HeaderValue::from_str(&header.value)
            .map_err(|error| format!("Invalid download header value: {error}"))?;
        builder = builder.header(name, value);
    }

    if let Some(body) = request.body {
        builder = builder.body(body);
    }

    let mut response = builder
        .send()
        .await
        .map_err(|error| format!("Download request failed: {error}"))?;
    let status = response.status();
    if !status.is_success() {
        let body = response
            .bytes()
            .await
            .map(|bytes| String::from_utf8_lossy(&bytes).into_owned())
            .unwrap_or_default();
        return Err(format!("{HTTP_ERROR_PREFIX}{}:{body}", status.as_u16()));
    }

    let mut file = fs::File::create(file_path)
        .map_err(|error| format!("Unable to create download file: {error}"))?;
    while let Some(chunk) = response
        .chunk()
        .await
        .map_err(|error| format!("Unable to read download stream: {error}"))?
    {
        file.write_all(&chunk)
            .map_err(|error| format!("Unable to write download file: {error}"))?;
    }
    file.flush()
        .map_err(|error| format!("Unable to flush download file: {error}"))?;
    Ok(())
}

fn safe_download_filename(filename: &str) -> String {
    let trimmed = filename.trim();
    if trimmed.is_empty() {
        return "download.bin".to_string();
    }

    Path::new(trimmed)
        .file_name()
        .and_then(|value| value.to_str())
        .filter(|value| !value.is_empty())
        .unwrap_or("download.bin")
        .to_string()
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![
            download_to_file,
            open_path_in_file_manager
        ])
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
