import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { OnboardingUpdate, SettingsUpdate } from "@tracegate/shared-types";

import { useApiClient } from "./clientContext";

export const queryKeys = {
  health: ["health"] as const,
  systemStatus: ["system-status"] as const,
  settings: ["settings"] as const,
  onboarding: ["onboarding"] as const,
};

export function useSystemStatus() {
  const client = useApiClient();
  return useQuery({
    queryKey: queryKeys.systemStatus,
    queryFn: ({ signal }) => client.getSystemStatus(signal),
    refetchInterval: 30_000,
    retry: 1,
  });
}

export function useSettings() {
  const client = useApiClient();
  return useQuery({
    queryKey: queryKeys.settings,
    queryFn: ({ signal }) => client.getSettings(signal),
    retry: 1,
  });
}

export function useUpdateSettings() {
  const client = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (update: SettingsUpdate) => client.updateSettings(update),
    onSuccess: (settings) => {
      queryClient.setQueryData(queryKeys.settings, settings);
    },
  });
}

export function useOnboarding() {
  const client = useApiClient();
  return useQuery({
    queryKey: queryKeys.onboarding,
    queryFn: ({ signal }) => client.getOnboarding(signal),
    retry: 1,
  });
}

export function useUpdateOnboarding() {
  const client = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (update: OnboardingUpdate) => client.updateOnboarding(update),
    onSuccess: (onboarding) => {
      queryClient.setQueryData(queryKeys.onboarding, onboarding);
      void queryClient.invalidateQueries({ queryKey: queryKeys.systemStatus });
    },
  });
}
