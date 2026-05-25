// SCAFFOLD — minimal Tauri 2.0 entry. Real desktop builds require:
//   1. rustup default stable
//   2. cargo install tauri-cli --version "^2.0"
//   3. npm i -D @tauri-apps/cli@^2.0 @tauri-apps/api@^2.0
//   4. (Windows) WebView2 runtime
//
// All app logic lives in the Vue/Vite frontend. The Rust shell only
// hosts the webview and forwards window events.

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![ping])
        .run(tauri::generate_context!())
        .expect("error while running EchoLens desktop");
}

#[tauri::command]
fn ping() -> &'static str {
    "pong from echolens-desktop"
}
