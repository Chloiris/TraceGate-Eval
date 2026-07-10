import { create } from "zustand";

export type StudioView = "dashboard" | "onboarding" | "settings";

interface UiState {
  activeView: StudioView;
  sidebarOpen: boolean;
  setActiveView: (view: StudioView) => void;
  setSidebarOpen: (open: boolean) => void;
}

export const useUiStore = create<UiState>((set) => ({
  activeView: "dashboard",
  sidebarOpen: false,
  setActiveView: (activeView) => set({ activeView, sidebarOpen: false }),
  setSidebarOpen: (sidebarOpen) => set({ sidebarOpen }),
}));
