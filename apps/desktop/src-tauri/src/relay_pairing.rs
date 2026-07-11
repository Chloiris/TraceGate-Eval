use std::time::Duration;

use serde::{Deserialize, Serialize};
use tauri::State;

use crate::{
    credentials::{self, CredentialKind, CredentialStatus},
    state::DesktopState,
};

#[derive(Debug, Deserialize)]
struct PairingResponse {
    device_token: String,
    repositories: Vec<String>,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct RelayPairingResult {
    repositories: Vec<String>,
    credential: CredentialStatus,
}

fn relay_endpoint(base_url: &str) -> Result<url::Url, String> {
    let mut url =
        url::Url::parse(base_url).map_err(|_| "Webhook Relay URL is invalid".to_owned())?;
    let loopback_http =
        url.scheme() == "http" && matches!(url.host_str(), Some("127.0.0.1" | "localhost" | "::1"));
    if url.scheme() != "https" && !loopback_http {
        return Err("Webhook Relay must use HTTPS or loopback HTTP".to_owned());
    }
    if !url.username().is_empty()
        || url.password().is_some()
        || url.query().is_some()
        || url.fragment().is_some()
    {
        return Err(
            "Webhook Relay URL must not contain credentials, query, or fragment".to_owned(),
        );
    }
    let path = format!("{}/v1/devices/pair", url.path().trim_end_matches('/'));
    url.set_path(&path);
    Ok(url)
}

fn valid_device_id(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= 128
        && value
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'_' | b'.' | b'-'))
}

fn valid_repository(value: &str) -> bool {
    let mut parts = value.split('/');
    let valid_part = |part: &str| {
        !part.is_empty()
            && part.len() <= 100
            && part
                .bytes()
                .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'_' | b'.' | b'-'))
    };
    matches!((parts.next(), parts.next(), parts.next()), (Some(owner), Some(repository), None) if valid_part(owner) && valid_part(repository))
}

#[tauri::command]
pub async fn pair_webhook_relay(
    base_url: String,
    pairing_code: String,
    device_id: String,
    state: State<'_, DesktopState>,
) -> Result<RelayPairingResult, String> {
    let endpoint = relay_endpoint(&base_url)?;
    if pairing_code.len() < 20
        || pairing_code.len() > 128
        || pairing_code.chars().any(char::is_whitespace)
    {
        return Err("Webhook Relay pairing code is invalid".to_owned());
    }
    if !valid_device_id(&device_id) {
        return Err("Webhook Relay device ID is invalid".to_owned());
    }
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(20))
        .redirect(reqwest::redirect::Policy::none())
        .user_agent("TraceGate-Studio/0.1")
        .build()
        .map_err(|_| "could not create Webhook Relay client".to_owned())?;
    let response = client
        .post(endpoint)
        .json(&serde_json::json!({
            "pairing_code": pairing_code,
            "device_id": device_id,
        }))
        .send()
        .await
        .map_err(|error| format!("Webhook Relay pairing request failed: {error}"))?;
    if !response.status().is_success() {
        return Err(format!(
            "Webhook Relay pairing returned HTTP {}",
            response.status().as_u16()
        ));
    }
    let mut payload: PairingResponse = response
        .json()
        .await
        .map_err(|_| "Webhook Relay pairing response was invalid".to_owned())?;
    if payload.repositories.is_empty()
        || payload.repositories.len() > 100
        || payload
            .repositories
            .iter()
            .any(|item| !valid_repository(item))
    {
        return Err("Webhook Relay pairing response contained invalid repository scope".to_owned());
    }
    payload.repositories.sort();
    payload.repositories.dedup();
    let credential = credentials::store_credential(CredentialKind::Relay, &payload.device_token)
        .map_err(|error| error.to_string())?;
    state
        .sidecar
        .apply_credential(CredentialKind::Relay, Some(&payload.device_token))
        .await
        .map_err(|error| {
            format!("Relay credential was saved securely but could not be applied live: {error}")
        })?;
    Ok(RelayPairingResult {
        repositories: payload.repositories,
        credential: credential.applied_live(),
    })
}

#[cfg(test)]
mod tests {
    use super::{relay_endpoint, valid_device_id, valid_repository};

    #[test]
    fn relay_pairing_accepts_https_or_loopback_and_strict_identifiers() {
        assert_eq!(
            relay_endpoint("https://relay.example.com/base")
                .expect("https relay")
                .as_str(),
            "https://relay.example.com/base/v1/devices/pair"
        );
        assert!(relay_endpoint("http://127.0.0.1:8080").is_ok());
        assert!(relay_endpoint("http://relay.example.com").is_err());
        assert!(relay_endpoint("https://user:secret@relay.example.com").is_err());
        assert!(valid_device_id("tracegate-mac-1"));
        assert!(!valid_device_id("bad device"));
        assert!(valid_repository("owner/repository"));
        assert!(!valid_repository("owner/repository/extra"));
    }
}
