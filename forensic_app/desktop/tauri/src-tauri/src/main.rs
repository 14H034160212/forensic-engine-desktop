// Forensic Engine — Tauri v2 shell.
// Spawns the bundled PyInstaller binary (the Python app) as a sidecar. The engine picks a FREE
// port (so it never collides with VS Code / other dev servers / a leftover instance) and writes
// it to ~/.forensic_engine/port. This shell reads that port, waits until the server answers, and
// navigates the window there via the native navigate() API. Everything stays on localhost.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::net::TcpStream;
use std::path::PathBuf;
use std::time::Duration;
use tauri::Manager;
use tauri_plugin_shell::{process::CommandEvent, ShellExt};

fn port_file() -> PathBuf {
    let home = std::env::var("USERPROFILE")
        .or_else(|_| std::env::var("HOME"))
        .unwrap_or_else(|_| ".".into());
    PathBuf::from(home).join(".forensic_engine").join("port")
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
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
                .env("NO_BROWSER", "1");
            let (mut rx, _child) = sidecar.spawn().expect("failed to spawn sidecar");
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
        .run(tauri::generate_context!())
        .expect("error while running Forensic Engine");
}
