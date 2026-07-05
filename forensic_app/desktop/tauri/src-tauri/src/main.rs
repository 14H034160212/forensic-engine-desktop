// Forensic Engine — Tauri v2 shell.
// Spawns the bundled PyInstaller binary (the Python app) as a sidecar, waits (Rust-side) until
// its local server answers, then navigates the window to it via the native navigate() API
// (more reliable than JS location.replace, which the webview can block). Everything stays on
// 127.0.0.1; nothing leaves the machine.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::net::TcpStream;
use std::time::Duration;
use tauri::Manager;
use tauri_plugin_shell::{process::CommandEvent, ShellExt};

const PORT: u16 = 8808;

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            let win = app.get_webview_window("main").unwrap();

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

            // 2) poll the port (whoever serves it — this sidecar or an already-running one),
            //    then navigate the window there. localhost (not 127.0.0.1) is a guaranteed
            //    secure context for the webview.
            let w2 = win.clone();
            tauri::async_runtime::spawn(async move {
                for _ in 0..240 {
                    if TcpStream::connect(("127.0.0.1", PORT)).is_ok() {
                        if let Ok(url) = tauri::Url::parse(&format!("http://localhost:{}/", PORT)) {
                            let _ = w2.navigate(url);
                        }
                        return;
                    }
                    std::thread::sleep(Duration::from_millis(500));
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
