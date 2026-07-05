// Forensic Engine — Tauri v2 shell.
// Spawns the bundled PyInstaller binary (the Python app) as a sidecar. The frontend splash page
// (frontend/index.html) polls http://127.0.0.1:8808 and navigates there once it answers — so we
// don't depend on a fixed timeout here. Everything stays on 127.0.0.1; nothing leaves the machine.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::{Emitter, Manager};
use tauri_plugin_shell::{process::CommandEvent, ShellExt};

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            let win = app.get_webview_window("main").unwrap();
            let sidecar = app
                .shell()
                .sidecar("engine-server")
                .expect("sidecar 'engine-server' not found")
                .env("NO_BROWSER", "1");
            let (mut rx, _child) = sidecar.spawn().expect("failed to spawn sidecar");

            // pump sidecar output; surface a crash to the splash page instead of hanging forever
            tauri::async_runtime::spawn(async move {
                while let Some(ev) = rx.recv().await {
                    match ev {
                        CommandEvent::Stdout(l) => println!("[engine] {}", String::from_utf8_lossy(&l)),
                        CommandEvent::Stderr(l) => eprintln!("[engine!] {}", String::from_utf8_lossy(&l)),
                        CommandEvent::Error(e) => {
                            let _ = win.eval(&format!(
                                "document.getElementById('s').textContent='engine failed to start: {}';",
                                e.replace('\'', " ")
                            ));
                        }
                        CommandEvent::Terminated(p) => {
                            let _ = win.emit("engine-exit", p.code);
                            let _ = win.eval(
                                "var s=document.getElementById('s'); if(s) s.textContent='the local engine stopped unexpectedly — please reopen the app.';",
                            );
                        }
                        _ => {}
                    }
                }
            });
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running Forensic Engine");
}
