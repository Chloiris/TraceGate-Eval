import { create } from "zustand";

export type StudioView =
  | "dashboard"
  | "repositories"
  | "pull-requests"
  | "pull-request-detail"
  | "repository-map"
  | "runs"
  | "eval"
  | "registry"
  | "diagnostics"
  | "onboarding"
  | "settings";

interface UiState {
  activeView: StudioView;
  sidebarOpen: boolean;
  selectedRepositoryId: string | null;
  selectedPullRequestId: string | null;
  selectedRunId: string | null;
  selectedFixSessionId: string | null;
  selectedDiffPath: string | null;
  setActiveView: (view: StudioView) => void;
  setSidebarOpen: (open: boolean) => void;
  selectRepository: (repositoryId: string, view?: StudioView) => void;
  selectPullRequest: (pullRequestId: string, repositoryId: string) => void;
  selectRun: (runId: string) => void;
  selectFixSession: (fixSessionId: string, pullRequestId: string, repositoryId: string) => void;
  selectDiffPath: (path: string) => void;
}

export const useUiStore = create<UiState>((set) => ({
  activeView: "dashboard",
  sidebarOpen: false,
  selectedRepositoryId: null,
  selectedPullRequestId: null,
  selectedRunId: null,
  selectedFixSessionId: null,
  selectedDiffPath: null,
  setActiveView: (activeView) => set({ activeView, sidebarOpen: false }),
  setSidebarOpen: (sidebarOpen) => set({ sidebarOpen }),
  selectRepository: (selectedRepositoryId, activeView = "repositories") =>
    set({ selectedRepositoryId, activeView, sidebarOpen: false }),
  selectPullRequest: (selectedPullRequestId, selectedRepositoryId) =>
    set({
      selectedPullRequestId,
      selectedRepositoryId,
      selectedRunId: null,
      selectedFixSessionId: null,
      selectedDiffPath: null,
      activeView: "pull-request-detail",
      sidebarOpen: false,
    }),
  selectRun: (selectedRunId) => set({ selectedRunId, activeView: "runs", sidebarOpen: false }),
  selectFixSession: (selectedFixSessionId, selectedPullRequestId, selectedRepositoryId) => set({
    selectedFixSessionId,
    selectedPullRequestId,
    selectedRepositoryId,
    activeView: "pull-request-detail",
    sidebarOpen: false,
  }),
  selectDiffPath: (selectedDiffPath) => set({ selectedDiffPath }),
}));
