// Forensic Engine — Tauri v2 shell.
// Spawns the bundled PyInstaller binary (the Python app) as a sidecar, waits for its local
// server to answer, then points the window at it. Everything stays on 127.0.0.1 — nothing
// leaves the machine.
//
// NOTE: this is a scaffold. It has NOT been compiled here (no Rust toolchain / target OS on the
// build box, and Tauri can't cross-compile). Build + iterate on a dev machine per the README.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::Manager;
use tauri_plugin_shell::{process::CommandEvent, ShellExt};

const PORT: u16 = 8808;

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            // 1) launch the Python app as a sidecar
            let sidecar = app.shell().sidecar("forensic-engine")
                .expect("sidecar 'forensic-engine' not found");
            let (mut rx, _child) = sidecar.spawn().expect("failed to spawn sidecar");
            tauri::async_runtime::spawn(async move {
                while let Some(ev) = rx.recv().await {
                    if let CommandEvent::Stdout(line) = ev {
                        println!("[engine] {}", String::from_utf8_lossy(&line));
                    }
                }
            });

            // 2) wait until the local server answers, then load it in the window
            let win = app.get_webview_window("main").unwrap();
            let url = format!("http://127.0.0.1:{}/", PORT);
            tauri::async_runtime::spawn(async move {
                for _ in 0..60 {
                    if reqwest_ok(&url).await { break; }
                    std::thread::sleep(std::time::Duration::from_millis(500));
                }
                let _ = win.eval(&format!("window.location.replace('{}')", url));
            });
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running Forensic Engine");
}

// tiny check without pulling a big HTTP client: try a TCP connect to the port
async fn reqwest_ok(_url: &str) -> bool {
    std::net::TcpStream::connect(("127.0.0.1", PORT)).is_ok()
}
