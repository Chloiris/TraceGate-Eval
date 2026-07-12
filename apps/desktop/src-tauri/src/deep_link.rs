use serde::Serialize;
use tauri::{AppHandle, Emitter, Manager, Runtime};
use thiserror::Error;
use url::Url;

use crate::{state::DesktopState, window};

pub const DEEP_LINK_EVENT: &str = "tracegate-deep-link";
const SCHEME: &str = "tracegate";

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum DeepLinkRoute {
    Repository {
        owner: String,
        repository: String,
    },
    PullRequest {
        owner: String,
        repository: String,
        number: u64,
    },
    Run {
        run_id: String,
    },
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
#[serde(rename_all = "camelCase")]
struct DeepLinkEvent {
    route: DeepLinkRoute,
    frontend_path: String,
}

impl DeepLinkRoute {
    pub fn frontend_path(&self) -> String {
        match self {
            Self::Repository { owner, repository } => {
                format!("/repositories/{owner}/{repository}")
            }
            Self::PullRequest {
                owner,
                repository,
                number,
            } => format!("/pull-requests/{owner}/{repository}/{number}"),
            Self::Run { run_id } => format!("/runs/{run_id}"),
        }
    }
}

#[derive(Debug, Error, PartialEq, Eq)]
pub enum DeepLinkError {
    #[error("deep link is not a valid URL")]
    InvalidUrl,
    #[error("deep link scheme is not tracegate")]
    InvalidScheme,
    #[error("deep link contains forbidden credentials, port, query, or fragment")]
    ForbiddenUrlPart,
    #[error("deep link route is not supported")]
    UnsupportedRoute,
    #[error("deep link path component is invalid")]
    InvalidComponent,
    #[error("Pull Request number must be a positive integer")]
    InvalidPullRequestNumber,
}

pub fn parse(raw: &str) -> Result<DeepLinkRoute, DeepLinkError> {
    let url = Url::parse(raw).map_err(|_| DeepLinkError::InvalidUrl)?;
    if url.scheme() != SCHEME {
        return Err(DeepLinkError::InvalidScheme);
    }
    if !url.username().is_empty()
        || url.password().is_some()
        || url.port().is_some()
        || url.query().is_some()
        || url.fragment().is_some()
    {
        return Err(DeepLinkError::ForbiddenUrlPart);
    }

    let route = url.host_str().ok_or(DeepLinkError::UnsupportedRoute)?;
    let segments = url
        .path_segments()
        .ok_or(DeepLinkError::UnsupportedRoute)?
        .collect::<Vec<_>>();

    match (route, segments.as_slice()) {
        ("repository", [owner, repository]) => {
            validate_component(owner, 100)?;
            validate_component(repository, 100)?;
            Ok(DeepLinkRoute::Repository {
                owner: (*owner).to_owned(),
                repository: (*repository).to_owned(),
            })
        }
        ("pr", [owner, repository, number]) => {
            validate_component(owner, 100)?;
            validate_component(repository, 100)?;
            let number = number
                .parse::<u64>()
                .map_err(|_| DeepLinkError::InvalidPullRequestNumber)?;
            if number == 0 {
                return Err(DeepLinkError::InvalidPullRequestNumber);
            }
            Ok(DeepLinkRoute::PullRequest {
                owner: (*owner).to_owned(),
                repository: (*repository).to_owned(),
                number,
            })
        }
        ("run", [run_id]) => {
            validate_component(run_id, 128)?;
            Ok(DeepLinkRoute::Run {
                run_id: (*run_id).to_owned(),
            })
        }
        _ => Err(DeepLinkError::UnsupportedRoute),
    }
}

fn validate_component(value: &str, max_len: usize) -> Result<(), DeepLinkError> {
    if value.is_empty()
        || value.len() > max_len
        || !value
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'-' | b'_' | b'.'))
    {
        return Err(DeepLinkError::InvalidComponent);
    }
    Ok(())
}

pub fn first_route<I, S>(arguments: I) -> Option<DeepLinkRoute>
where
    I: IntoIterator<Item = S>,
    S: AsRef<str>,
{
    arguments
        .into_iter()
        .find_map(|argument| parse(argument.as_ref()).ok())
}

pub fn deliver<R: Runtime>(app: &AppHandle<R>, route: DeepLinkRoute) {
    stage(app, route);
    let _ = window::show_main_window(app);
}

pub fn stage<R: Runtime>(app: &AppHandle<R>, route: DeepLinkRoute) {
    app.state::<DesktopState>()
        .set_pending_deep_link(route.clone());
    let event = DeepLinkEvent {
        frontend_path: route.frontend_path(),
        route,
    };
    let _ = app.emit(DEEP_LINK_EVENT, event);
}

pub fn deliver_from_arguments<R, I, S>(app: &AppHandle<R>, arguments: I) -> bool
where
    R: Runtime,
    I: IntoIterator<Item = S>,
    S: AsRef<str>,
{
    if let Some(route) = first_route(arguments) {
        deliver(app, route);
        true
    } else {
        false
    }
}

#[cfg(test)]
mod tests {
    use super::{first_route, parse, DeepLinkError, DeepLinkRoute};

    #[test]
    fn parses_repository_route() {
        let route = parse("tracegate://repository/openai/codex").unwrap();
        assert_eq!(
            route,
            DeepLinkRoute::Repository {
                owner: "openai".into(),
                repository: "codex".into(),
            }
        );
        assert_eq!(route.frontend_path(), "/repositories/openai/codex");
    }

    #[test]
    fn parses_pull_request_and_run_routes() {
        assert_eq!(
            parse("tracegate://pr/openai/codex/42").unwrap(),
            DeepLinkRoute::PullRequest {
                owner: "openai".into(),
                repository: "codex".into(),
                number: 42,
            }
        );
        assert_eq!(
            parse("tracegate://run/018f3d4a-7f20-7b9d-a3c2-123456789abc").unwrap(),
            DeepLinkRoute::Run {
                run_id: "018f3d4a-7f20-7b9d-a3c2-123456789abc".into(),
            }
        );
    }

    #[test]
    fn rejects_untrusted_or_ambiguous_links() {
        assert_eq!(
            parse("https://repository/openai/codex"),
            Err(DeepLinkError::InvalidScheme)
        );
        assert_eq!(
            parse("tracegate://user:password@repository/openai/codex"),
            Err(DeepLinkError::ForbiddenUrlPart)
        );
        assert_eq!(
            parse("tracegate://repository/openai/codex?token=hidden"),
            Err(DeepLinkError::ForbiddenUrlPart)
        );
        assert!(parse("tracegate://repository/openai/%2e%2e").is_err());
        assert_eq!(
            parse("tracegate://pr/openai/codex/0"),
            Err(DeepLinkError::InvalidPullRequestNumber)
        );
    }

    #[test]
    fn scans_arguments_without_trusting_unrelated_values() {
        let route = first_route(["--flag", "tracegate://run/run-123", "secret=value"]);
        assert_eq!(
            route,
            Some(DeepLinkRoute::Run {
                run_id: "run-123".into(),
            })
        );
    }
}
