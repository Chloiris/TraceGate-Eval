/* eslint-disable react-refresh/only-export-components -- provider and its required typed hook share one private context. */
import { createContext, useContext, type PropsWithChildren } from "react";
import type { TraceGateApiClient } from "@tracegate/api-client";

const ApiClientContext = createContext<TraceGateApiClient | null>(null);

interface ApiClientProviderProps extends PropsWithChildren {
  client: TraceGateApiClient;
}

export function ApiClientProvider({ client, children }: ApiClientProviderProps) {
  return <ApiClientContext value={client}>{children}</ApiClientContext>;
}

export function useApiClient(): TraceGateApiClient {
  const client = useContext(ApiClientContext);
  if (client === null) {
    throw new Error("ApiClientProvider is missing");
  }
  return client;
}
