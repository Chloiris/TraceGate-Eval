import { useEffect, useState } from "react";
import { TraceGateApiClient } from "@tracegate/api-client";

import { ApiClientProvider } from "./api/clientContext";
import { ErrorState, LoadingState } from "./components/RequestState";
import { createHostBridge, type HostBridge } from "./host/hostBridge";
import { errorMessage } from "./lib/errors";
import { StudioShell } from "./StudioShell";

type RuntimeState =
  | { state: "loading" }
  | { state: "ready"; client: TraceGateApiClient }
  | { state: "error"; error: unknown };

const defaultHost = createHostBridge();
const TAURI_CONNECTION_ATTEMPTS = 120;
const TAURI_CONNECTION_INTERVAL_MS = 250;

async function connectToHost(host: HostBridge): Promise<TraceGateApiClient> {
  const attempts = host.kind === "tauri" ? TAURI_CONNECTION_ATTEMPTS : 1;
  let lastError: unknown;
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    try {
      return new TraceGateApiClient(await host.getApiConnection());
    } catch (error) {
      lastError = error;
      if (attempt + 1 < attempts) {
        await new Promise((resolve) => window.setTimeout(resolve, TAURI_CONNECTION_INTERVAL_MS));
      }
    }
  }
  throw lastError;
}

export interface AppProps {
  host?: HostBridge;
}

export function App({ host = defaultHost }: AppProps) {
  const [runtime, setRuntime] = useState<RuntimeState>({ state: "loading" });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    setRuntime({ state: "loading" });
    void connectToHost(host)
      .then((client) => {
        if (active) {
          setRuntime({ state: "ready", client });
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setRuntime({ state: "error", error });
        }
      });
    return () => {
      active = false;
    };
  }, [attempt, host]);

  if (runtime.state === "loading") {
    return (
      <StartupFrame>
        <LoadingState label="正在从宿主取得临时 API 连接信息…" />
        <StartupChecks backend="检查中" github="等待后端" model="等待后端" />
      </StartupFrame>
    );
  }

  if (runtime.state === "error") {
    return (
      <StartupFrame>
        <ErrorState
          title="本地后端尚未连接"
          message={errorMessage(runtime.error)}
          onRetry={() => setAttempt((value) => value + 1)}
        />
        <StartupChecks backend="未配置或不可用" github="无法检查" model="无法检查" />
      </StartupFrame>
    );
  }

  return (
    <ApiClientProvider client={runtime.client}>
      <StudioShell host={host} />
    </ApiClientProvider>
  );
}

function StartupFrame({ children }: { children: React.ReactNode }) {
  return (
    <main className="startup-screen">
      <div className="startup-card">
        <div className="brand-lockup startup-brand">
          <span className="brand-mark" aria-hidden="true"><i />TG</span>
          <div>
            <strong>TraceGate Studio</strong>
            <span>SECURE LOCAL STARTUP</span>
          </div>
        </div>
        <div className="startup-copy">
          <span className="eyebrow">正在建立可信本地会话</span>
          <h1>连接真实后端后再展示数据</h1>
          <p>系统不会在连接失败时切换到 mock、fixture 或规则生成的正常报告。</p>
        </div>
        {children}
      </div>
    </main>
  );
}

function StartupChecks({ backend, github, model }: { backend: string; github: string; model: string }) {
  return (
    <dl className="startup-checks">
      <div><dt>本地后端</dt><dd>{backend}</dd></div>
      <div><dt>GitHub</dt><dd>{github}</dd></div>
      <div><dt>模型</dt><dd>{model}</dd></div>
    </dl>
  );
}
