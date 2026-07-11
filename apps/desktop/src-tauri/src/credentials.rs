use keyring::{Entry, Error as KeyringError};
use serde::{Deserialize, Serialize};
use thiserror::Error;

const SERVICE: &str = "io.tracegate.studio";
const MIN_SECRET_LENGTH: usize = 20;
const MAX_SECRET_LENGTH: usize = 8192;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum CredentialKind {
    Github,
    Model,
    Relay,
}

impl CredentialKind {
    fn account(self) -> &'static str {
        match self {
            Self::Github => "github-token",
            Self::Model => "model-api-key",
            Self::Relay => "webhook-relay-device-token",
        }
    }

    pub fn environment_name(self) -> &'static str {
        match self {
            Self::Github => "GITHUB_TOKEN",
            Self::Model => "TRACEGATE_LLM_API_KEY",
            Self::Relay => "TRACEGATE_RELAY_DEVICE_TOKEN",
        }
    }

    pub fn api_name(self) -> &'static str {
        match self {
            Self::Github => "github",
            Self::Model => "model",
            Self::Relay => "relay",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct CredentialStatus {
    pub kind: CredentialKind,
    pub configured: bool,
    pub storage: &'static str,
    pub restart_required_after_change: bool,
}

impl CredentialStatus {
    pub fn applied_live(mut self) -> Self {
        self.restart_required_after_change = false;
        self
    }

    pub fn with_live_refresh_available(mut self, available: bool) -> Self {
        self.restart_required_after_change = !available;
        self
    }
}

#[derive(Debug, Error)]
pub enum CredentialError {
    #[error("secure credential storage is only available on supported desktop platforms")]
    UnsupportedPlatform,
    #[error("credential must contain between 20 and 8192 non-whitespace characters")]
    InvalidSecret,
    #[error("the operating-system credential store operation failed")]
    Store,
}

fn storage_label() -> Result<&'static str, CredentialError> {
    #[cfg(target_os = "macos")]
    return Ok("macOS Keychain");
    #[cfg(target_os = "windows")]
    return Ok("Windows Credential Manager");
    #[allow(unreachable_code)]
    Err(CredentialError::UnsupportedPlatform)
}

fn entry(kind: CredentialKind) -> Result<Entry, CredentialError> {
    storage_label()?;
    Entry::new(SERVICE, kind.account()).map_err(|_| CredentialError::Store)
}

pub fn read_credential(kind: CredentialKind) -> Result<Option<String>, CredentialError> {
    match entry(kind)?.get_password() {
        Ok(secret) => Ok(Some(secret)),
        Err(KeyringError::NoEntry) => Ok(None),
        Err(_) => Err(CredentialError::Store),
    }
}

pub fn credential_status(kind: CredentialKind) -> Result<CredentialStatus, CredentialError> {
    Ok(CredentialStatus {
        kind,
        configured: read_credential(kind)?.is_some(),
        storage: storage_label()?,
        restart_required_after_change: true,
    })
}

pub fn store_credential(
    kind: CredentialKind,
    secret: &str,
) -> Result<CredentialStatus, CredentialError> {
    if secret.len() < MIN_SECRET_LENGTH
        || secret.len() > MAX_SECRET_LENGTH
        || secret.chars().any(char::is_whitespace)
    {
        return Err(CredentialError::InvalidSecret);
    }
    entry(kind)?
        .set_password(secret)
        .map_err(|_| CredentialError::Store)?;
    credential_status(kind)
}

pub fn delete_credential(kind: CredentialKind) -> Result<CredentialStatus, CredentialError> {
    match entry(kind)?.delete_credential() {
        Ok(()) | Err(KeyringError::NoEntry) => credential_status(kind),
        Err(_) => Err(CredentialError::Store),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn kinds_map_to_distinct_non_secret_accounts_and_environment_names() {
        assert_ne!(
            CredentialKind::Github.account(),
            CredentialKind::Model.account()
        );
        assert_eq!(CredentialKind::Github.environment_name(), "GITHUB_TOKEN");
        assert_eq!(
            CredentialKind::Model.environment_name(),
            "TRACEGATE_LLM_API_KEY"
        );
        assert_eq!(
            CredentialKind::Relay.environment_name(),
            "TRACEGATE_RELAY_DEVICE_TOKEN"
        );
        assert_eq!(CredentialKind::Github.api_name(), "github");
        assert_eq!(CredentialKind::Model.api_name(), "model");
        assert_eq!(CredentialKind::Relay.api_name(), "relay");
    }

    #[test]
    fn status_serialization_contains_no_secret_field() {
        let value = serde_json::to_value(CredentialStatus {
            kind: CredentialKind::Github,
            configured: true,
            storage: "test secure store",
            restart_required_after_change: true,
        })
        .expect("status serialization");
        assert_eq!(value["configured"], true);
        assert_eq!(value["restartRequiredAfterChange"], true);
        let live_value = serde_json::to_value(
            CredentialStatus {
                kind: CredentialKind::Github,
                configured: true,
                storage: "test secure store",
                restart_required_after_change: true,
            }
            .applied_live(),
        )
        .expect("live status serialization");
        assert_eq!(live_value["restartRequiredAfterChange"], false);
        assert!(value.get("secret").is_none());
        assert!(value.get("token").is_none());
    }

    #[test]
    #[cfg(any(target_os = "macos", target_os = "windows"))]
    #[ignore = "explicitly mutates then deletes a dedicated platform verification credential"]
    fn native_secure_store_round_trip() {
        struct DeleteOnDrop(Entry);
        impl Drop for DeleteOnDrop {
            fn drop(&mut self) {
                let _ = self.0.delete_credential();
            }
        }

        let entry = Entry::new("io.tracegate.studio.verification", "native-round-trip")
            .expect("platform credential entry");
        let guard = DeleteOnDrop(entry);
        guard
            .0
            .set_password("tracegate-verification-only-credential")
            .expect("store verification credential");
        assert_eq!(
            guard
                .0
                .get_password()
                .expect("read verification credential"),
            "tracegate-verification-only-credential"
        );
        guard
            .0
            .delete_credential()
            .expect("delete verification credential");
        assert!(matches!(guard.0.get_password(), Err(KeyringError::NoEntry)));
    }
}
