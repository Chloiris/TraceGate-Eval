use std::{
    ffi::{OsStr, OsString},
    fmt::Write as _,
    net::TcpListener,
    sync::{
        atomic::{AtomicBool, Ordering},
        Arc, Mutex,
    },
    time::Duration,
};

use rand::{rngs::OsRng, RngCore};
use serde::Serialize;
use tauri::{AppHandle, Emitter, Manager};
use tauri_plugin_shell::{
    process::{CommandChild, CommandEvent},
    ShellExt,
};
use thiserror::Error;

use crate::{
    credentials::{read_credential, CredentialKind},
    platform,
};

pub const SIDECAR_STATUS_EVENT: &str = "tracegate-sidecar-status";
pub const SIDECAR_LOGICAL_NAME: &str = "tracegate-backend";
pub const SIDECAR_SUBCOMMAND: &str = "serve";
pub const LOOPBACK_HOST: &str = "127.0.0.1";
pub const HEALTH_PATH: &str = "/api/v1/health";
pub const API_PREFIX: &str = "/api/v1";
pub const CREDENTIAL_CONTROL_PREFIX: &str = "/internal/v1/credentials";
pub const MAX_RESTARTS: u8 = 2;
const HEALTH_ATTEMPTS: usize = 120;
const HEALTH_INTERVAL: Duration = Duration::from_millis(250);

const ALLOWED_PARENT_ENVIRONMENT: &[&str] = &[
    "APPDATA",
    "HOME",
    "LANG",
    "LC_ALL",
    "LOCALAPPDATA",
    "PATH",
    "SystemRoot",
    "TEMP",
    "TMP",
    "TZ",
    "USERPROFILE",
    "WINDIR",
];

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
#[serde(tag = "state", rename_all = "SCREAMING_SNAKE_CASE")]
pub enum SidecarStatus {
    Stopped,
    Starting { attempt: u8 },
    Healthy { origin: String, pid: u32 },
    Restarting { attempt: u8, reason: String },
    Failed { reason: String },
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ApiConnection {
    pub base_url: String,
    pub token: String,
}

#[derive(Debug, Error)]
enum SidecarError {
    #[error("the current OS/architecture has no supported Sidecar target")]
    UnsupportedTarget,
    #[error("failed to resolve the application-data directory: {0}")]
    AppData(String),
    #[error("failed to create the application-data directory: {0}")]
    CreateAppData(String),
    #[error("failed to reserve a loopback port: {0}")]
    ReservePort(String),
    #[error("failed to create the Sidecar command: {0}")]
    CreateCommand(String),
    #[error("failed to spawn the Sidecar: {0}")]
    Spawn(String),
    #[error("failed to read {0} from operating-system credential storage")]
    SecureStorage(&'static str),
    #[error("Sidecar health check timed out")]
    HealthTimeout,
    #[error("Sidecar process exited unexpectedly")]
    ProcessExited,
    #[error("Sidecar process event stream failed")]
    ProcessEvent,
}

struct SupervisorInner {
    child: Mutex<Option<CommandChild>>,
    connection: Mutex<Option<ApiConnection>>,
    credential_control: Mutex<Option<CredentialControl>>,
    running: AtomicBool,
    shutdown: AtomicBool,
    status: Mutex<SidecarStatus>,
}

#[derive(Clone)]
struct CredentialControl {
    origin: String,
    token: String,
}

#[derive(Clone)]
pub struct SidecarSupervisor {
    inner: Arc<SupervisorInner>,
}

impl Default for SidecarSupervisor {
    fn default() -> Self {
        Self {
            inner: Arc::new(SupervisorInner {
                child: Mutex::new(None),
                connection: Mutex::new(None),
                credential_control: Mutex::new(None),
                running: AtomicBool::new(false),
                shutdown: AtomicBool::new(false),
                status: Mutex::new(SidecarStatus::Stopped),
            }),
        }
    }
}

impl SidecarSupervisor {
    pub fn status(&self) -> SidecarStatus {
        self.inner
            .status
            .lock()
            .expect("Sidecar status mutex poisoned")
            .clone()
    }

    pub fn api_connection(&self) -> Option<ApiConnection> {
        self.inner
            .connection
            .lock()
            .expect("Sidecar connection mutex poisoned")
            .clone()
    }

    pub fn credential_refresh_available(&self) -> bool {
        self.inner
            .credential_control
            .lock()
            .map(|control| control.is_some())
            .unwrap_or(false)
    }

    pub fn start(&self, app: AppHandle) {
        if self.inner.running.swap(true, Ordering::AcqRel) {
            return;
        }
        self.inner.shutdown.store(false, Ordering::Release);
        let supervisor = self.clone();
        tauri::async_runtime::spawn(async move {
            supervisor.supervise(app).await;
        });
    }

    pub async fn apply_credential(
        &self,
        kind: CredentialKind,
        secret: Option<&str>,
    ) -> Result<(), String> {
        let control = self
            .inner
            .credential_control
            .lock()
            .map_err(|_| "Sidecar credential-control state is unavailable".to_owned())?
            .clone()
            .ok_or_else(|| {
                "TraceGate backend is not healthy; credential refresh is unavailable".to_owned()
            })?;
        let client = reqwest::Client::builder()
            .connect_timeout(Duration::from_secs(2))
            .timeout(Duration::from_secs(5))
            .redirect(reqwest::redirect::Policy::none())
            .build()
            .map_err(|_| "could not create the Sidecar credential-refresh client".to_owned())?;
        let url = format!(
            "{}{}/{}",
            control.origin,
            CREDENTIAL_CONTROL_PREFIX,
            kind.api_name()
        );
        let request = match secret {
            Some(value) => client
                .put(url)
                .bearer_auth(&control.token)
                .json(&serde_json::json!({ "secret": value })),
            None => client.delete(url).bearer_auth(&control.token),
        };
        let response = request
            .send()
            .await
            .map_err(|_| "Sidecar credential refresh request failed".to_owned())?;
        if !response.status().is_success() {
            return Err(format!(
                "Sidecar credential refresh returned HTTP {}",
                response.status().as_u16()
            ));
        }
        Ok(())
    }

    pub fn shutdown<R: tauri::Runtime>(&self, app: &AppHandle<R>) {
        self.inner.shutdown.store(true, Ordering::Release);
        self.set_connection(None);
        self.set_credential_control(None);
        if let Some(child) = self
            .inner
            .child
            .lock()
            .expect("Sidecar child mutex poisoned")
            .take()
        {
            terminate_child(child);
        }
        self.update_status(app, SidecarStatus::Stopped);
    }

    async fn supervise(&self, app: AppHandle) {
        for restart_index in 0..=MAX_RESTARTS {
            if self.is_shutting_down() {
                break;
            }

            let attempt = restart_index + 1;
            self.update_status(&app, SidecarStatus::Starting { attempt });
            match self.run_once(&app).await {
                Ok(()) => break,
                Err(error) if restart_index < MAX_RESTARTS && !self.is_shutting_down() => {
                    self.update_status(
                        &app,
                        SidecarStatus::Restarting {
                            attempt: attempt + 1,
                            reason: error.to_string(),
                        },
                    );
                    tokio::time::sleep(Duration::from_secs(u64::from(attempt))).await;
                }
                Err(error) => {
                    if !self.is_shutting_down() {
                        self.update_status(
                            &app,
                            SidecarStatus::Failed {
                                reason: error.to_string(),
                            },
                        );
                    }
                    break;
                }
            }
        }

        self.inner.running.store(false, Ordering::Release);
        if self.is_shutting_down() {
            self.update_status(&app, SidecarStatus::Stopped);
        }
    }

    async fn run_once(&self, app: &AppHandle) -> Result<(), SidecarError> {
        self.set_connection(None);
        platform::sidecar_binary_name().ok_or(SidecarError::UnsupportedTarget)?;
        let app_data = app
            .path()
            .app_data_dir()
            .map_err(|error| SidecarError::AppData(error.to_string()))?;
        std::fs::create_dir_all(&app_data)
            .map_err(|error| SidecarError::CreateAppData(error.to_string()))?;

        let port = reserve_loopback_port()?;
        let origin = format!("http://{LOOPBACK_HOST}:{port}");
        let token = generate_token();
        let credential_control_token = generate_token();
        let environment = filter_environment(std::env::vars_os());

        let mut command = app
            .shell()
            .sidecar(SIDECAR_LOGICAL_NAME)
            .map_err(|error| SidecarError::CreateCommand(error.to_string()))?
            .args([SIDECAR_SUBCOMMAND])
            .env_clear()
            .envs(environment)
            .env("TRACEGATE_HOST", LOOPBACK_HOST)
            .env("TRACEGATE_PORT", port.to_string())
            .env("TRACEGATE_LOCAL_API_TOKEN", &token)
            .env(
                "TRACEGATE_CREDENTIAL_CONTROL_TOKEN",
                &credential_control_token,
            )
            .env("TRACEGATE_DATA_DIR", &app_data)
            .env("TRACEGATE_PARENT_WATCHDOG", "1")
            .env("TRACEGATE_DESKTOP_PID", std::process::id().to_string())
            .env(
                "TRACEGATE_RUST_VERSION_INFO",
                format!(
                    "minimum toolchain {}; desktop crate {}",
                    option_env!("CARGO_PKG_RUST_VERSION").unwrap_or("unspecified"),
                    env!("CARGO_PKG_VERSION")
                ),
            )
            .current_dir(&app_data);

        for kind in [
            CredentialKind::Github,
            CredentialKind::Model,
            CredentialKind::Relay,
        ] {
            if let Some(secret) = read_credential(kind)
                .map_err(|_| SidecarError::SecureStorage(kind.environment_name()))?
            {
                command = command.env(kind.environment_name(), secret);
            }
        }

        let (mut events, child) = command
            .spawn()
            .map_err(|error| SidecarError::Spawn(error.to_string()))?;
        let pid = child.pid();
        *self
            .inner
            .child
            .lock()
            .expect("Sidecar child mutex poisoned") = Some(child);

        if !wait_until_healthy(&origin, &token, || self.is_shutting_down()).await {
            self.stop_current_child();
            if self.is_shutting_down() {
                return Ok(());
            }
            return Err(SidecarError::HealthTimeout);
        }

        self.set_credential_control(Some(CredentialControl {
            origin: origin.clone(),
            token: credential_control_token,
        }));
        self.set_connection(Some(ApiConnection {
            base_url: format!("{origin}{API_PREFIX}"),
            token,
        }));

        self.update_status(
            app,
            SidecarStatus::Healthy {
                origin: origin.clone(),
                pid,
            },
        );

        while let Some(event) = events.recv().await {
            match event {
                CommandEvent::Terminated(_) => {
                    self.clear_current_child();
                    return if self.is_shutting_down() {
                        Ok(())
                    } else {
                        Err(SidecarError::ProcessExited)
                    };
                }
                CommandEvent::Error(_) => {
                    self.stop_current_child();
                    return if self.is_shutting_down() {
                        Ok(())
                    } else {
                        Err(SidecarError::ProcessEvent)
                    };
                }
                CommandEvent::Stdout(_) | CommandEvent::Stderr(_) => {
                    // Sidecar output can contain repository data. The desktop shell does not
                    // mirror it to stdout or frontend events.
                }
                _ => {}
            }
        }

        self.clear_current_child();
        if self.is_shutting_down() {
            Ok(())
        } else {
            Err(SidecarError::ProcessExited)
        }
    }

    fn is_shutting_down(&self) -> bool {
        self.inner.shutdown.load(Ordering::Acquire)
    }

    fn clear_current_child(&self) {
        self.set_connection(None);
        self.set_credential_control(None);
        self.inner
            .child
            .lock()
            .expect("Sidecar child mutex poisoned")
            .take();
    }

    fn stop_current_child(&self) {
        self.set_connection(None);
        self.set_credential_control(None);
        if let Some(child) = self
            .inner
            .child
            .lock()
            .expect("Sidecar child mutex poisoned")
            .take()
        {
            terminate_child(child);
        }
    }

    fn set_connection(&self, connection: Option<ApiConnection>) {
        *self
            .inner
            .connection
            .lock()
            .expect("Sidecar connection mutex poisoned") = connection;
    }

    fn set_credential_control(&self, control: Option<CredentialControl>) {
        *self
            .inner
            .credential_control
            .lock()
            .expect("Sidecar credential-control mutex poisoned") = control;
    }

    fn update_status<R: tauri::Runtime>(&self, app: &AppHandle<R>, status: SidecarStatus) {
        *self
            .inner
            .status
            .lock()
            .expect("Sidecar status mutex poisoned") = status.clone();
        let _ = app.emit(SIDECAR_STATUS_EVENT, status);
        if matches!(self.status(), SidecarStatus::Failed { .. }) {
            let _ = crate::commands::show_actionable_notification(
                app.clone(),
                "TraceGate Studio".to_owned(),
                "The local Sidecar could not restart. Open Diagnostics for details.".to_owned(),
                None,
            );
        }
    }
}

fn terminate_child(child: CommandChild) {
    #[cfg(unix)]
    let pid = child.pid();
    let _ = child.kill();
    #[cfg(unix)]
    unsafe {
        // PyInstaller one-file bootloaders may retain SIGTERM. SIGKILL is a
        // bounded fallback for the bootloader; the Python worker observes the
        // parent loss and requests its own Uvicorn shutdown.
        libc::kill(pid as libc::pid_t, libc::SIGKILL);
    }
}

fn reserve_loopback_port() -> Result<u16, SidecarError> {
    let listener = TcpListener::bind((LOOPBACK_HOST, 0))
        .map_err(|error| SidecarError::ReservePort(error.to_string()))?;
    listener
        .local_addr()
        .map(|address| address.port())
        .map_err(|error| SidecarError::ReservePort(error.to_string()))
}

fn generate_token() -> String {
    let mut bytes = [0_u8; 32];
    OsRng.fill_bytes(&mut bytes);
    let mut token = String::with_capacity(64);
    for byte in bytes {
        write!(&mut token, "{byte:02x}").expect("writing to a String cannot fail");
    }
    token
}

fn filter_environment<I>(variables: I) -> Vec<(OsString, OsString)>
where
    I: IntoIterator<Item = (OsString, OsString)>,
{
    variables
        .into_iter()
        .filter(|(key, _)| {
            ALLOWED_PARENT_ENVIRONMENT
                .iter()
                .any(|allowed| key.as_os_str() == OsStr::new(allowed))
        })
        .collect()
}

async fn wait_until_healthy<F>(origin: &str, token: &str, is_shutting_down: F) -> bool
where
    F: Fn() -> bool,
{
    let client = match reqwest::Client::builder()
        .connect_timeout(Duration::from_millis(500))
        .timeout(Duration::from_secs(1))
        .build()
    {
        Ok(client) => client,
        Err(_) => return false,
    };
    let url = format!("{origin}{HEALTH_PATH}");

    for _ in 0..HEALTH_ATTEMPTS {
        if is_shutting_down() {
            return false;
        }
        if let Ok(response) = client.get(&url).bearer_auth(token).send().await {
            if response.status().is_success() {
                return true;
            }
        }
        tokio::time::sleep(HEALTH_INTERVAL).await;
    }
    false
}

#[cfg(test)]
mod tests {
    use std::{
        ffi::OsString,
        io::{Read, Write},
        net::{TcpListener, TcpStream},
        sync::{Arc, Mutex},
        thread,
        time::Duration,
    };

    use super::{
        filter_environment, generate_token, ApiConnection, CredentialControl, SidecarStatus,
        SidecarSupervisor, API_PREFIX, CREDENTIAL_CONTROL_PREFIX, HEALTH_PATH, MAX_RESTARTS,
        SIDECAR_SUBCOMMAND,
    };
    use crate::credentials::CredentialKind;

    fn read_request(mut stream: TcpStream) -> String {
        stream
            .set_read_timeout(Some(Duration::from_secs(5)))
            .expect("set request timeout");
        let mut bytes = Vec::new();
        let mut chunk = [0_u8; 1024];
        let expected_length = loop {
            let count = stream.read(&mut chunk).expect("read request");
            assert!(count > 0, "request ended before headers");
            bytes.extend_from_slice(&chunk[..count]);
            if let Some(header_end) = bytes.windows(4).position(|window| window == b"\r\n\r\n") {
                let headers = String::from_utf8_lossy(&bytes[..header_end]);
                let content_length = headers
                    .lines()
                    .find_map(|line| {
                        let (name, value) = line.split_once(':')?;
                        (name.eq_ignore_ascii_case("content-length"))
                            .then(|| value.trim().parse::<usize>().expect("content length"))
                    })
                    .unwrap_or(0);
                break header_end + 4 + content_length;
            }
        };
        while bytes.len() < expected_length {
            let count = stream.read(&mut chunk).expect("read request body");
            assert!(count > 0, "request ended before body");
            bytes.extend_from_slice(&chunk[..count]);
        }
        stream
            .write_all(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\n{}")
            .expect("write response");
        String::from_utf8(bytes).expect("request is utf-8")
    }

    #[test]
    fn token_has_256_bits_encoded_as_hex() {
        let first = generate_token();
        let second = generate_token();
        assert_eq!(first.len(), 64);
        assert!(first.bytes().all(|byte| byte.is_ascii_hexdigit()));
        assert_ne!(first, second);
    }

    #[test]
    fn child_environment_drops_credentials() {
        let filtered = filter_environment(
            [
                ("PATH", "/usr/bin"),
                ("HOME", "/tmp/home"),
                ("GITHUB_TOKEN", "secret"),
                ("DEEPSEEK_API_KEY", "secret"),
                ("SSH_AUTH_SOCK", "/tmp/agent"),
            ]
            .into_iter()
            .map(|(key, value)| (OsString::from(key), OsString::from(value))),
        );
        let keys = filtered
            .iter()
            .map(|(key, _)| key.to_string_lossy().into_owned())
            .collect::<Vec<_>>();
        assert_eq!(keys, ["PATH", "HOME"]);
    }

    #[test]
    fn retry_and_health_contracts_are_bounded() {
        assert_eq!(MAX_RESTARTS, 2);
        assert_eq!(HEALTH_PATH, "/api/v1/health");
        assert_eq!(CREDENTIAL_CONTROL_PREFIX, "/internal/v1/credentials");
        assert_eq!(SIDECAR_SUBCOMMAND, "serve");
        assert_eq!(super::HEALTH_ATTEMPTS, 120);
    }

    #[test]
    fn api_credentials_are_absent_from_status_serialization() {
        let supervisor = super::SidecarSupervisor::default();
        let connection = ApiConnection {
            base_url: format!("http://127.0.0.1:43123{API_PREFIX}"),
            token: "private-test-token".into(),
        };
        supervisor.set_connection(Some(connection.clone()));
        *supervisor.inner.status.lock().unwrap() = SidecarStatus::Healthy {
            origin: "http://127.0.0.1:43123".into(),
            pid: 123,
        };

        assert_eq!(supervisor.api_connection(), Some(connection.clone()));
        let serialized_status = serde_json::to_string(&supervisor.status()).unwrap();
        assert!(!serialized_status.contains(&connection.base_url));
        assert!(!serialized_status.contains(&connection.token));
        assert!(!serialized_status.contains(API_PREFIX));
    }

    #[test]
    fn credential_refresh_uses_private_control_channel_without_replacing_api_connection() {
        let listener = TcpListener::bind(("127.0.0.1", 0)).expect("bind control server");
        let origin = format!("http://{}", listener.local_addr().expect("control address"));
        let requests = Arc::new(Mutex::new(Vec::new()));
        let captured = requests.clone();
        let server = thread::spawn(move || {
            for stream in listener.incoming().take(2) {
                captured
                    .lock()
                    .expect("request capture")
                    .push(read_request(stream.expect("control request")));
            }
        });

        let supervisor = SidecarSupervisor::default();
        let public_connection = ApiConnection {
            base_url: "http://127.0.0.1:43123/api/v1".to_owned(),
            token: "public-api-token-not-for-control".to_owned(),
        };
        supervisor.set_connection(Some(public_connection.clone()));
        supervisor.set_credential_control(Some(CredentialControl {
            origin,
            token: "private-control-token-not-for-webview".to_owned(),
        }));
        let runtime = tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .build()
            .expect("test runtime");
        runtime.block_on(async {
            supervisor
                .apply_credential(
                    CredentialKind::Github,
                    Some("not-a-real-github-credential-value"),
                )
                .await
                .expect("apply live credential");
            supervisor
                .apply_credential(CredentialKind::Github, None)
                .await
                .expect("delete live credential");
        });
        server.join().expect("control server completed");

        let requests = requests.lock().expect("captured requests");
        assert_eq!(requests.len(), 2);
        assert!(requests[0].starts_with("PUT /internal/v1/credentials/github "));
        assert!(requests[1].starts_with("DELETE /internal/v1/credentials/github "));
        for request in requests.iter() {
            let normalized = request.to_ascii_lowercase();
            assert!(
                normalized.contains("authorization: bearer private-control-token-not-for-webview")
            );
            assert!(!request.contains(&public_connection.token));
        }
        assert_eq!(supervisor.api_connection(), Some(public_connection));
    }
}
