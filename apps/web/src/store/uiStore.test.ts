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
});
