import { afterEach, describe, expect, it, vi } from "vitest";

import { BrowserHost, GITHUB_FINE_GRAINED_PAT_CREATION_URL, TauriHost } from "./hostBridge";

const invokeMock = vi.hoisted(() => vi.fn());

vi.mock("@tauri-apps/api/core", () => ({ invoke: invokeMock }));

const githubTokenUrl = GITHUB_FINE_GRAINED_PAT_CREATION_URL;

afterEach(() => {
  vi.restoreAllMocks();
});

describe("HostBridge.openExternal", () => {
  it("invokes the allowlisted desktop command with the URL unchanged", async () => {
    invokeMock.mockResolvedValue(undefined);

    await new TauriHost().openExternal(githubTokenUrl);

    expect(invokeMock).toHaveBeenCalledWith("open_external", { url: githubTokenUrl });
  });

  it("opens the allowlisted page in a protected browser tab", async () => {
    const open = vi.spyOn(window, "open").mockReturnValue({} as Window);
    const host = new BrowserHost({
      VITE_TRACEGATE_API_BASE_URL: "/api/v1",
      VITE_TRACEGATE_API_TOKEN: "test-only-token",
    });

    await host.openExternal(githubTokenUrl);

    expect(open).toHaveBeenCalledWith(githubTokenUrl, "_blank", "noopener,noreferrer");
  });

  it("rejects non-allowlisted external URLs before invoking a host", async () => {
    const host = new TauriHost();

    await expect(host.openExternal("https://github.com/chologonia/TraceGate-Eval"))
      .rejects.toMatchObject({
        name: "HostBridgeError",
        code: "unsupported_host",
      });
    expect(invokeMock).not.toHaveBeenCalled();
  });

  it("reports a browser popup blocker instead of pretending the page opened", async () => {
    vi.spyOn(window, "open").mockReturnValue(null);
    const host = new BrowserHost({
      VITE_TRACEGATE_API_BASE_URL: "/api/v1",
      VITE_TRACEGATE_API_TOKEN: "test-only-token",
    });

    await expect(host.openExternal(githubTokenUrl)).rejects.toMatchObject({
      name: "HostBridgeError",
      code: "host_command_failed",
    });
  });
});
