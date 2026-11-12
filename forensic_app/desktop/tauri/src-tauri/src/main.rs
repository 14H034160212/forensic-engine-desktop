// Forensic Engine — Tauri v2 shell.
// Spawns the bundled PyInstaller binary (the Python app) as a sidecar. The engine picks a FREE
// port (so it never collides with VS Code / other dev servers / a leftover instance) and writes
// it to ~/.forensic_engine/port. This shell reads that port, waits until the server answers, and
// navigates the window there via the native navigate() API. Everything stays on localhost.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::net::TcpStream;
use std::path::PathBuf;
use std::sync::Mutex;
use std::time::Duration;
use tauri::Manager;
use tauri_plugin_shell::{
    process::{CommandChild, CommandEvent},
    ShellExt,
};

// Handle to the spawned engine so RunEvent::Exit can kill it.
struct EngineChild(Mutex<Option<CommandChild>>);

fn port_file() -> PathBuf {
    let home = std::env::var("USERPROFILE")
        .or_else(|_| std::env::var("HOME"))
        .unwrap_or_else(|_| ".".into());
    PathBuf::from(home).join(".forensic_engine").join("port")
}

// Open a URL in the user's SYSTEM browser. The webview blocks target=_blank and the served page has no
// reliable plugin JS binding, so the frontend calls this via core.invoke — a dependable path that keeps
// the app window on the analysis SPA (info/download links never navigate the window away).
#[tauri::command]
fn open_external(app: tauri::AppHandle, url: String) -> Result<(), String> {
    app.shell().open(url, None).map_err(|e| e.to_string())
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![open_external])
        .setup(|app| {
            let win = app.get_webview_window("main").unwrap();

            // stale port from a previous run must not be read as the new one
            let pf = port_file();
            let _ = std::fs::remove_file(&pf);

            // 1) launch the Python app as a sidecar (NO_BROWSER so it doesn't pop a system tab)
            let sidecar = app
                .shell()
                .sidecar("engine-server")
                .expect("sidecar 'engine-server' not found")
                .env("NO_BROWSER", "1")
                // the engine polls this PID and exits when we're gone (covers crash / force-quit)
                .env("FE_PARENT_PID", std::process::id().to_string());
            let (mut rx, child) = sidecar.spawn().expect("failed to spawn sidecar");
            // keep the handle so we can kill the engine on a normal quit (see RunEvent::Exit below)
            app.manage(EngineChild(Mutex::new(Some(child))));
            tauri::async_runtime::spawn(async move {
                while let Some(ev) = rx.recv().await {
                    match ev {
                        CommandEvent::Stdout(l) => println!("[engine] {}", String::from_utf8_lossy(&l)),
                        CommandEvent::Stderr(l) => eprintln!("[engine!] {}", String::from_utf8_lossy(&l)),
                        _ => {}
                    }
                }
            });

            // 2) wait for the engine to publish its port, then for that port to answer, then navigate
            let w2 = win.clone();
            tauri::async_runtime::spawn(async move {
                let mut port: Option<u16> = None;
                for _ in 0..240 {
                    if let Ok(s) = std::fs::read_to_string(&pf) {
                        if let Ok(p) = s.trim().parse::<u16>() {
                            port = Some(p);
                            break;
                        }
                    }
                    std::thread::sleep(Duration::from_millis(500));
                }
                if let Some(p) = port {
                    for _ in 0..240 {
                        if TcpStream::connect(("127.0.0.1", p)).is_ok() {
                            if let Ok(url) = tauri::Url::parse(&format!("http://localhost:{}/", p)) {
                                let _ = w2.navigate(url);
                            }
                            return;
                        }
                        std::thread::sleep(Duration::from_millis(500));
                    }
                }
                let _ = w2.eval(
                    "var s=document.getElementById('s'); if(s) s.textContent='the local engine did not come up — please reopen the app.';",
                );
            });
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building Forensic Engine")
        .run(|app, event| {
            // Cmd+Q / closing the last window: stop the Python engine instead of orphaning it.
            if let tauri::RunEvent::Exit = event {
                if let Some(state) = app.try_state::<EngineChild>() {
                    if let Some(child) = state.0.lock().unwrap().take() {
                        let _ = child.kill();
                    }
                }
            }
        });
}
