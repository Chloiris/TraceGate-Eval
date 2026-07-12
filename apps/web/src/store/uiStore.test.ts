import { beforeEach, describe, expect, it } from "vitest";

import { useUiStore } from "./uiStore";

describe("UI store", () => {
  beforeEach(() => {
    useUiStore.setState({ activeView: "dashboard", sidebarOpen: true });
  });

  it("changes views and closes the mobile sidebar", () => {
    useUiStore.getState().setActiveView("settings");

    expect(useUiStore.getState()).toMatchObject({
      activeView: "settings",
      sidebarOpen: false,
    });
  });

  it("opens a hash-bound Fix Session deep link in its owning PR", () => {
    useUiStore.getState().selectFixSession(
      "11111111-1111-4111-8111-111111111111",
      "22222222-2222-4222-8222-222222222222",
      "33333333-3333-4333-8333-333333333333",
    );
    expect(useUiStore.getState()).toMatchObject({
      activeView: "pull-request-detail",
      selectedFixSessionId: "11111111-1111-4111-8111-111111111111",
      selectedPullRequestId: "22222222-2222-4222-8222-222222222222",
      selectedRepositoryId: "33333333-3333-4333-8333-333333333333",
      sidebarOpen: false,
    });
  });
});
