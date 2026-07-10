import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { OnboardingUpdate, RepositoryCreate, RepositoryUpdate, SettingsUpdate } from "@tracegate/shared-types";

import { useApiClient } from "./clientContext";

export const queryKeys = {
  health: ["health"] as const,
  systemStatus: ["system-status"] as const,
  settings: ["settings"] as const,
  onboarding: ["onboarding"] as const,
  repositories: ["repositories"] as const,
  pullRequests: (repositoryId?: string) => ["pull-requests", repositoryId ?? "all"] as const,
  repositoryGraph: (repositoryId: string) => ["repository-graph", repositoryId] as const,
  pullRequest: (pullRequestId: string) => ["pull-request", pullRequestId] as const,
  pullRequestDiff: (pullRequestId: string, path?: string) => ["pull-request-diff", pullRequestId, path ?? "first"] as const,
  pullRequestGraph: (pullRequestId: string) => ["pull-request-graph", pullRequestId] as const,
  pullRequestTour: (pullRequestId: string) => ["pull-request-tour", pullRequestId] as const,
  runs: (pullRequestId?: string) => ["runs", pullRequestId ?? "all"] as const,
  findings: (runId?: string) => ["findings", runId ?? "all"] as const,
  evidence: (runId?: string) => ["evidence", runId ?? "all"] as const,
  evaluations: ["evaluations"] as const,
  agents: ["agents"] as const,
  tools: ["tools"] as const,
  diagnostics: ["diagnostics"] as const,
  updateStatus: ["update-status"] as const,
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

export function useRepositories() {
  const client = useApiClient();
  return useQuery({
    queryKey: queryKeys.repositories,
    queryFn: ({ signal }) => client.listRepositories(signal),
    retry: 1,
  });
}

export function useCreateRepository() {
  const client = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: RepositoryCreate) => client.createRepository(input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.repositories });
      void queryClient.invalidateQueries({ queryKey: queryKeys.onboarding });
    },
  });
}

export function useUpdateRepository() {
  const client = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ repositoryId, update }: { repositoryId: string; update: RepositoryUpdate }) =>
      client.updateRepository(repositoryId, update),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: queryKeys.repositories }),
  });
}

export function useDeleteRepository() {
  const client = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (repositoryId: string) => client.deleteRepository(repositoryId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.repositories });
      void queryClient.invalidateQueries({ queryKey: ["pull-requests"] });
    },
  });
}

export function useSyncRepository() {
  const client = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (repositoryId: string) => client.syncRepository(repositoryId),
    onSuccess: (_result, repositoryId) => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.repositories });
      void queryClient.invalidateQueries({ queryKey: queryKeys.pullRequests(repositoryId) });
    },
  });
}

export function useIndexRepository() {
  const client = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (repositoryId: string) => client.indexRepository(repositoryId),
    onSuccess: (_result, repositoryId) => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.repositories });
      void queryClient.invalidateQueries({ queryKey: queryKeys.repositoryGraph(repositoryId) });
    },
  });
}

export function usePullRequests(repositoryId?: string) {
  const client = useApiClient();
  return useQuery({
    queryKey: queryKeys.pullRequests(repositoryId),
    queryFn: ({ signal }) => client.listPullRequests(repositoryId, signal),
    retry: 1,
  });
}

export function usePullRequest(pullRequestId?: string) {
  const client = useApiClient();
  return useQuery({
    queryKey: queryKeys.pullRequest(pullRequestId ?? "none"),
    queryFn: ({ signal }) => client.getPullRequest(pullRequestId ?? "", signal),
    enabled: Boolean(pullRequestId),
    retry: 1,
  });
}

export function usePullRequestDiff(pullRequestId?: string, path?: string) {
  const client = useApiClient();
  return useQuery({
    queryKey: queryKeys.pullRequestDiff(pullRequestId ?? "none", path),
    queryFn: ({ signal }) => client.getPullRequestDiff(pullRequestId ?? "", path, signal),
    enabled: Boolean(pullRequestId),
    retry: 1,
  });
}

export function usePullRequestGraph(pullRequestId?: string) {
  const client = useApiClient();
  return useQuery({
    queryKey: queryKeys.pullRequestGraph(pullRequestId ?? "none"),
    queryFn: ({ signal }) => client.getPullRequestGraph(pullRequestId ?? "", signal),
    enabled: Boolean(pullRequestId),
    retry: 1,
  });
}

export function usePullRequestTour(pullRequestId?: string) {
  const client = useApiClient();
  return useQuery({
    queryKey: queryKeys.pullRequestTour(pullRequestId ?? "none"),
    queryFn: ({ signal }) => client.getPullRequestTour(pullRequestId ?? "", signal),
    enabled: Boolean(pullRequestId),
    retry: 1,
  });
}

export function useRepositoryGraph(repositoryId?: string) {
  const client = useApiClient();
  return useQuery({
    queryKey: queryKeys.repositoryGraph(repositoryId ?? "none"),
    queryFn: ({ signal }) => client.getRepositoryGraph(repositoryId ?? "", signal),
    enabled: Boolean(repositoryId),
    retry: 1,
  });
}

export function useAnalyzePullRequest() {
  const client = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ pullRequestId, force = false }: { pullRequestId: string; force?: boolean }) =>
      client.analyzePullRequest(pullRequestId, force),
    onSuccess: (result) => {
      void queryClient.invalidateQueries({ queryKey: ["runs"] });
      void queryClient.invalidateQueries({ queryKey: queryKeys.pullRequest(result.run.pull_request_id ?? "none") });
    },
  });
}

export function useRuns(pullRequestId?: string) {
  const client = useApiClient();
  return useQuery({
    queryKey: queryKeys.runs(pullRequestId),
    queryFn: ({ signal }) => client.listRuns(pullRequestId, signal),
    refetchInterval: (query) =>
      query.state.data?.items.some((item) => item.status === "queued" || item.status === "running") ? 1_000 : false,
    retry: 1,
  });
}

export function useRun(runId?: string) {
  const client = useApiClient();
  return useQuery({
    queryKey: ["run", runId ?? "none"],
    queryFn: ({ signal }) => client.getRun(runId ?? "", signal),
    enabled: Boolean(runId),
    refetchInterval: (query) =>
      query.state.data?.status === "queued" || query.state.data?.status === "running" ? 1_000 : false,
    retry: 1,
  });
}

export function useRunEvidenceGraph(runId?: string) {
  const client = useApiClient();
  return useQuery({
    queryKey: ["run-evidence-graph", runId ?? "none"],
    queryFn: ({ signal }) => client.getRunEvidenceGraph(runId ?? "", signal),
    enabled: Boolean(runId),
    retry: 1,
  });
}

export function useCancelRun() {
  const client = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (runId: string) => client.cancelRun(runId),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["runs"] }),
  });
}

export function useRetryRun() {
  const client = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (runId: string) => client.retryRun(runId),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["runs"] }),
  });
}

export function useFindings(runId?: string) {
  const client = useApiClient();
  return useQuery({
    queryKey: queryKeys.findings(runId),
    queryFn: ({ signal }) => client.listFindings(runId, signal),
    enabled: Boolean(runId),
    retry: 1,
  });
}

export function useEvidence(runId?: string) {
  const client = useApiClient();
  return useQuery({
    queryKey: queryKeys.evidence(runId),
    queryFn: ({ signal }) => client.listEvidence(runId, signal),
    enabled: Boolean(runId),
    retry: 1,
  });
}

export function useEvaluations() {
  const client = useApiClient();
  return useQuery({
    queryKey: queryKeys.evaluations,
    queryFn: ({ signal }) => client.getEvaluations(signal),
    retry: 1,
  });
}

export function useAgents() {
  const client = useApiClient();
  return useQuery({
    queryKey: queryKeys.agents,
    queryFn: ({ signal }) => client.listAgents(signal),
    retry: 1,
  });
}

export function useTools() {
  const client = useApiClient();
  return useQuery({
    queryKey: queryKeys.tools,
    queryFn: ({ signal }) => client.listTools(signal),
    retry: 1,
  });
}

export function useDiagnostics() {
  const client = useApiClient();
  return useQuery({
    queryKey: queryKeys.diagnostics,
    queryFn: ({ signal }) => client.getDiagnostics(signal),
    refetchInterval: 10_000,
    retry: 1,
  });
}

export function useUpdateStatus() {
  const client = useApiClient();
  return useQuery({
    queryKey: queryKeys.updateStatus,
    queryFn: ({ signal }) => client.getUpdateStatus(signal),
    retry: 1,
  });
}
