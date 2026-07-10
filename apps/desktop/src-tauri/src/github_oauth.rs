use std::{
    sync::Mutex,
    time::{Duration, Instant, SystemTime, UNIX_EPOCH},
};

use serde::{Deserialize, Serialize};
use tauri::State;

use crate::credentials::{self, CredentialKind, CredentialStatus};

const DEVICE_CODE_URL: &str = "https://github.com/login/device/code";
const ACCESS_TOKEN_URL: &str = "https://github.com/login/oauth/access_token";
const VERIFICATION_URI: &str = "https://github.com/login/device";

#[derive(Debug)]
struct OAuthSession {
    client_id: String,
    device_code: String,
    expires_at: Instant,
    interval: Duration,
    next_poll: Instant,
}

#[derive(Default)]
pub struct GitHubOAuthState(Mutex<Option<OAuthSession>>);

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct DeviceAuthorization {
    user_code: String,
    verification_uri: &'static str,
    expires_at_epoch_ms: u128,
    interval_seconds: u64,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct DevicePollResult {
    status: &'static str,
    interval_seconds: u64,
    credential: Option<CredentialStatus>,
}

#[derive(Debug, Deserialize)]
struct DeviceCodePayload {
    device_code: String,
    user_code: String,
    verification_uri: String,
    expires_in: u64,
    interval: Option<u64>,
}

#[derive(Debug, Deserialize)]
struct AccessTokenPayload {
    access_token: Option<String>,
    error: Option<String>,
    interval: Option<u64>,
}

fn validate_client_id(client_id: &str) -> Result<(), String> {
    if client_id.is_empty()
        || client_id.len() > 255
        || !client_id.is_ascii()
        || client_id.chars().any(char::is_whitespace)
    {
        return Err("GitHub OAuth client ID is invalid".to_owned());
    }
    Ok(())
}

fn validate_device_payload(payload: &DeviceCodePayload) -> Result<(), String> {
    if payload.verification_uri != VERIFICATION_URI
        || payload.device_code.len() < 20
        || payload.device_code.len() > 1024
        || payload.user_code.is_empty()
        || payload.user_code.len() > 128
        || payload.expires_in == 0
        || payload.expires_in > 3600
        || !(1..=60).contains(&payload.interval.unwrap_or(5))
    {
        return Err("GitHub returned an invalid device authorization response".to_owned());
    }
    Ok(())
}

fn github_client() -> Result<reqwest::Client, String> {
    reqwest::Client::builder()
        .timeout(Duration::from_secs(20))
        .redirect(reqwest::redirect::Policy::none())
        .user_agent("TraceGate-Studio/0.1")
        .build()
        .map_err(|_| "could not create GitHub OAuth client".to_owned())
}

#[tauri::command]
pub async fn begin_github_device_flow(
    client_id: String,
    state: State<'_, GitHubOAuthState>,
) -> Result<DeviceAuthorization, String> {
    validate_client_id(&client_id)?;
    let response = github_client()?
        .post(DEVICE_CODE_URL)
        .header("Accept", "application/json")
        .form(&[
            ("client_id", client_id.as_str()),
            ("scope", "read:user repo"),
        ])
        .send()
        .await
        .map_err(|error| format!("GitHub device authorization request failed: {error}"))?;
    if !response.status().is_success() {
        return Err(format!(
            "GitHub device authorization returned HTTP {}",
            response.status().as_u16()
        ));
    }
    let payload: DeviceCodePayload = response
        .json()
        .await
        .map_err(|_| "GitHub device authorization response was not valid JSON".to_owned())?;
    validate_device_payload(&payload)?;
    let interval = Duration::from_secs(payload.interval.unwrap_or(5));
    let expires_at_epoch_ms = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_err(|_| "system clock is before the Unix epoch".to_owned())?
        .as_millis()
        + u128::from(payload.expires_in) * 1000;
    *state
        .0
        .lock()
        .map_err(|_| "GitHub OAuth state is unavailable".to_owned())? = Some(OAuthSession {
        client_id,
        device_code: payload.device_code,
        expires_at: Instant::now() + Duration::from_secs(payload.expires_in),
        interval,
        next_poll: Instant::now(),
    });
    Ok(DeviceAuthorization {
        user_code: payload.user_code,
        verification_uri: VERIFICATION_URI,
        expires_at_epoch_ms,
        interval_seconds: interval.as_secs(),
    })
}

#[tauri::command]
pub async fn poll_github_device_flow(
    state: State<'_, GitHubOAuthState>,
) -> Result<DevicePollResult, String> {
    let (client_id, device_code, interval) = {
        let mut guard = state
            .0
            .lock()
            .map_err(|_| "GitHub OAuth state is unavailable".to_owned())?;
        let session = guard
            .as_mut()
            .ok_or_else(|| "No GitHub device authorization is active".to_owned())?;
        if Instant::now() >= session.expires_at {
            *guard = None;
            return Err("GitHub device authorization expired".to_owned());
        }
        if Instant::now() < session.next_poll {
            return Ok(DevicePollResult {
                status: "pending",
                interval_seconds: session.interval.as_secs(),
                credential: None,
            });
        }
        session.next_poll = Instant::now() + session.interval;
        (
            session.client_id.clone(),
            session.device_code.clone(),
            session.interval,
        )
    };
    let response = github_client()?
        .post(ACCESS_TOKEN_URL)
        .header("Accept", "application/json")
        .form(&[
            ("client_id", client_id.as_str()),
            ("device_code", device_code.as_str()),
            ("grant_type", "urn:ietf:params:oauth:grant-type:device_code"),
        ])
        .send()
        .await
        .map_err(|error| format!("GitHub access-token request failed: {error}"))?;
    if !response.status().is_success() {
        return Err(format!(
            "GitHub access-token request returned HTTP {}",
            response.status().as_u16()
        ));
    }
    let payload: AccessTokenPayload = response
        .json()
        .await
        .map_err(|_| "GitHub access-token response was not valid JSON".to_owned())?;
    match payload.error.as_deref() {
        Some("authorization_pending") => Ok(DevicePollResult {
            status: "pending",
            interval_seconds: interval.as_secs(),
            credential: None,
        }),
        Some("slow_down") => {
            let mut guard = state
                .0
                .lock()
                .map_err(|_| "GitHub OAuth state is unavailable".to_owned())?;
            if let Some(session) = guard.as_mut() {
                session.interval = Duration::from_secs(
                    payload
                        .interval
                        .unwrap_or(session.interval.as_secs() + 5)
                        .min(60),
                );
                session.next_poll = Instant::now() + session.interval;
                return Ok(DevicePollResult {
                    status: "pending",
                    interval_seconds: session.interval.as_secs(),
                    credential: None,
                });
            }
            Err("GitHub OAuth state disappeared".to_owned())
        }
        Some("expired_token" | "access_denied") => {
            *state
                .0
                .lock()
                .map_err(|_| "GitHub OAuth state is unavailable".to_owned())? = None;
            Err(format!(
                "GitHub device authorization failed: {}",
                payload.error.as_deref().unwrap_or("unknown")
            ))
        }
        Some(error) => Err(format!("GitHub device authorization failed: {error}")),
        None => {
            let token = payload
                .access_token
                .ok_or_else(|| "GitHub access-token response did not contain a token".to_owned())?;
            let credential = credentials::store_credential(CredentialKind::Github, &token)
                .map_err(|error| error.to_string())?;
            *state
                .0
                .lock()
                .map_err(|_| "GitHub OAuth state is unavailable".to_owned())? = None;
            Ok(DevicePollResult {
                status: "authorized",
                interval_seconds: interval.as_secs(),
                credential: Some(credential),
            })
        }
    }
}

#[cfg(test)]
mod tests {
    use super::{validate_client_id, validate_device_payload, DeviceCodePayload, VERIFICATION_URI};

    #[test]
    fn device_flow_rejects_untrusted_identifiers_and_verification_urls() {
        assert!(validate_client_id("Iv1.tracegate-client").is_ok());
        assert!(validate_client_id("bad client").is_err());
        let mut payload = DeviceCodePayload {
            device_code: "d".repeat(40),
            user_code: "ABCD-EFGH".to_owned(),
            verification_uri: VERIFICATION_URI.to_owned(),
            expires_in: 900,
            interval: Some(5),
        };
        assert!(validate_device_payload(&payload).is_ok());
        payload.verification_uri = "https://example.invalid/device".to_owned();
        assert!(validate_device_payload(&payload).is_err());
    }
}
