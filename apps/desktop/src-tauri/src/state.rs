use std::sync::{
    atomic::{AtomicBool, Ordering},
    Mutex,
};

use serde::Serialize;

use crate::{
    deep_link::DeepLinkRoute,
    platform,
    sidecar::{SidecarStatus, SidecarSupervisor},
};

pub struct DesktopState {
    quitting: AtomicBool,
    pending_deep_link: Mutex<Option<DeepLinkRoute>>,
    pub sidecar: SidecarSupervisor,
}

impl Default for DesktopState {
    fn default() -> Self {
        Self {
            quitting: AtomicBool::new(false),
            pending_deep_link: Mutex::new(None),
            sidecar: SidecarSupervisor::default(),
        }
    }
}

impl DesktopState {
    pub fn begin_quit(&self) {
        self.quitting.store(true, Ordering::Release);
    }

    pub fn is_quitting(&self) -> bool {
        self.quitting.load(Ordering::Acquire)
    }

    pub fn set_pending_deep_link(&self, route: DeepLinkRoute) {
        *self
            .pending_deep_link
            .lock()
            .expect("pending deep-link mutex poisoned") = Some(route);
    }

    pub fn take_pending_deep_link(&self) -> Option<DeepLinkRoute> {
        self.pending_deep_link
            .lock()
            .expect("pending deep-link mutex poisoned")
            .take()
    }

    pub fn snapshot(&self) -> DesktopStatus {
        DesktopStatus {
            platform: platform::platform_name(),
            expected_sidecar_binary: platform::sidecar_binary_name(),
            quitting: self.is_quitting(),
            sidecar: self.sidecar.status(),
        }
    }
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct DesktopStatus {
    pub platform: &'static str,
    pub expected_sidecar_binary: Option<&'static str>,
    pub quitting: bool,
    pub sidecar: SidecarStatus,
}

#[cfg(test)]
mod tests {
    use super::DesktopState;
    use crate::deep_link::DeepLinkRoute;

    #[test]
    fn quit_and_pending_route_state_are_explicit() {
        let state = DesktopState::default();
        assert!(!state.is_quitting());
        assert!(state.take_pending_deep_link().is_none());

        let route = DeepLinkRoute::Run {
            run_id: "run-1".into(),
        };
        state.set_pending_deep_link(route.clone());
        assert_eq!(state.take_pending_deep_link(), Some(route));
        assert!(state.take_pending_deep_link().is_none());

        state.begin_quit();
        assert!(state.is_quitting());
    }
}
