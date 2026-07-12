import { useMutation, useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query";
import type {
  FixActionRequest,
  FixApplyRequest,
  FixConfirmationRequest,
  FixPlanRequest,
  FixSessionCreate,
  FixSessionDetail,
  OnboardingUpdate,
  RepositoryCreate,
  RepositoryUpdate,
  SettingsUpdate,
} from "@tracegate/shared-types";

import { useApiClient } from "./clientContext";

export const queryKeys = {
  health: ["health"] as const,
  systemStatus: ["system-status"] as const,
  settings: ["settings"] as const,
  onboarding: ["onboarding"] as const,
  repositories: ["repositories"] as const,
  repositorySummary: (repositoryId: string) => ["repository-summary", repositoryId] as const,
  pullRequests: (repositoryId?: string) => ["pull-requests", repositoryId ?? "all"] as const,
  repositoryGraph: (repositoryId: string) => ["repository-graph", repositoryId] as const,
  pullRequest: (pullRequestId: string) => ["pull-request", pullRequestId] as const,
  pullRequestChecks: (pullRequestId: string) => ["pull-request-checks", pullRequestId] as const,
  pullRequestCommits: (pullRequestId: string) => ["pull-request-commits", pullRequestId] as const,
  pullRequestFiles: (pullRequestId: string) => ["pull-request-files", pullRequestId] as const,
  pullRequestDiff: (pullRequestId: string, path?: string) => ["pull-request-diff", pullRequestId, path ?? "first"] as const,
  pullRequestGraph: (pullRequestId: string) => ["pull-request-graph", pullRequestId] as const,
  pullRequestTour: (pullRequestId: string) => ["pull-request-tour", pullRequestId] as const,
  runs: (pullRequestId?: string) => ["runs", pullRequestId ?? "all"] as const,
  findings: (runId?: string) => ["findings", runId ?? "all"] as const,
  evidence: (runId?: string) => ["evidence", runId ?? "all"] as const,
  fixSessions: (pullRequestId?: string, findingId?: string) => ["fix-sessions", pullRequestId ?? "all", findingId ?? "all"] as const,
  fixSession: (fixSessionId: string) => ["fix-session", fixSessionId] as const,
  fixPatch: (fixSessionId: string, path?: string) => ["fix-patch", fixSessionId, path ?? "all"] as const,
  fixReport: (fixSessionId: string) => ["fix-report", fixSessionId] as const,
  fixWorkspaces: ["fix-workspaces"] as const,
  evaluations: ["evaluations"] as const,
  agents: ["agents"] as const,
  tools: ["tools"] as const,
  diagnostics: ["diagnostics"] as const,
  updateStatus: ["update-status"] as const,
};

function storeFixSession(queryClient: QueryClient, session: FixSessionDetail): void {
  queryClient.setQueryData(queryKeys.fixSession(session.id), session);
  void queryClient.invalidateQueries({ queryKey: ["fix-sessions"] });
}

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

export function useClearRepositoryCache() {
  const client = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (repositoryId: string) => client.clearRepositoryCache(repositoryId),
    onSuccess: (_result, repositoryId) => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.repositories });
      void queryClient.invalidateQueries({ queryKey: queryKeys.repositorySummary(repositoryId) });
      void queryClient.removeQueries({ queryKey: queryKeys.repositoryGraph(repositoryId) });
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
      void queryClient.invalidateQueries({ queryKey: ["pull-request-checks"] });
      void queryClient.invalidateQueries({ queryKey: ["pull-request-commits"] });
      void queryClient.invalidateQueries({ queryKey: ["pull-request-files"] });
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
      void queryClient.invalidateQueries({ queryKey: queryKeys.repositorySummary(repositoryId) });
    },
  });
}

export function useRepositorySummary(repositoryId?: string) {
  const client = useApiClient();
  return useQuery({
    queryKey: queryKeys.repositorySummary(repositoryId ?? "none"),
    queryFn: ({ signal }) => client.getRepositorySummary(repositoryId ?? "", signal),
    enabled: Boolean(repositoryId),
    retry: 1,
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

export function usePullRequestChecks(pullRequestId?: string) {
  const client = useApiClient();
  return useQuery({
    queryKey: queryKeys.pullRequestChecks(pullRequestId ?? "none"),
    queryFn: ({ signal }) => client.listCheckRuns(pullRequestId ?? "", signal),
    enabled: Boolean(pullRequestId),
    retry: 1,
  });
}

export function usePullRequestCommits(pullRequestId?: string) {
  const client = useApiClient();
  return useQuery({
    queryKey: queryKeys.pullRequestCommits(pullRequestId ?? "none"),
    queryFn: ({ signal }) => client.listPullRequestCommits(pullRequestId ?? "", signal),
    enabled: Boolean(pullRequestId),
    retry: 1,
  });
}

export function usePullRequestFiles(pullRequestId?: string) {
  const client = useApiClient();
  return useQuery({
    queryKey: queryKeys.pullRequestFiles(pullRequestId ?? "none"),
    queryFn: ({ signal }) => client.listPullRequestFiles(pullRequestId ?? "", signal),
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

export function useFixSessions(pullRequestId?: string, findingId?: string) {
  const client = useApiClient();
  return useQuery({
    queryKey: queryKeys.fixSessions(pullRequestId, findingId),
    queryFn: ({ signal }) => client.listFixSessions({
      ...(pullRequestId ? { pullRequestId } : {}),
      ...(findingId ? { findingId } : {}),
    }, signal),
    refetchInterval: 5_000,
    retry: 1,
  });
}

export function useFixSession(fixSessionId?: string) {
  const client = useApiClient();
  return useQuery({
    queryKey: queryKeys.fixSession(fixSessionId ?? "none"),
    queryFn: ({ signal }) => client.getFixSession(fixSessionId ?? "", signal),
    enabled: Boolean(fixSessionId),
    retry: 1,
  });
}

export function useFixPatch(fixSessionId?: string, path?: string) {
  const client = useApiClient();
  return useQuery({
    queryKey: queryKeys.fixPatch(fixSessionId ?? "none", path),
    queryFn: ({ signal }) => client.getFixPatch(fixSessionId ?? "", path, signal),
    enabled: Boolean(fixSessionId),
    retry: 1,
  });
}

export function useFixReport(fixSessionId?: string) {
  const client = useApiClient();
  return useQuery({
    queryKey: queryKeys.fixReport(fixSessionId ?? "none"),
    queryFn: ({ signal }) => client.getFixReport(fixSessionId ?? "", signal),
    enabled: Boolean(fixSessionId),
    retry: 1,
  });
}

export function useCreateFixSession() {
  const client = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: FixSessionCreate) => client.createFixSession(input),
    onSuccess: (session) => storeFixSession(queryClient, session),
  });
}

export function usePlanFixSession() {
  const client = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ fixSessionId, input }: { fixSessionId: string; input: FixPlanRequest }) =>
      client.planFixSession(fixSessionId, input),
    onSuccess: (session) => storeFixSession(queryClient, session),
  });
}

export function useGenerateFixPatch() {
  const client = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ fixSessionId, input }: { fixSessionId: string; input: FixActionRequest }) =>
      client.generateFixPatch(fixSessionId, input),
    onSuccess: (session) => {
      storeFixSession(queryClient, session);
      void queryClient.invalidateQueries({ queryKey: ["fix-patch", session.id] });
    },
  });
}

export function useConfirmFixSession() {
  const client = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ fixSessionId, input }: { fixSessionId: string; input: FixConfirmationRequest }) =>
      client.confirmFixSession(fixSessionId, input),
    onSuccess: (session) => storeFixSession(queryClient, session),
  });
}

export function useApplyFixSession() {
  const client = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ fixSessionId, input }: { fixSessionId: string; input: FixApplyRequest }) =>
      client.applyFixSession(fixSessionId, input),
    onSuccess: (session) => {
      storeFixSession(queryClient, session);
      void queryClient.invalidateQueries({ queryKey: ["fix-patch", session.id] });
    },
  });
}

export function useValidateFixSession() {
  const client = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ fixSessionId, input }: { fixSessionId: string; input: FixActionRequest }) =>
      client.validateFixSession(fixSessionId, input),
    onSuccess: (session) => storeFixSession(queryClient, session),
  });
}

export function useRereviewFixSession() {
  const client = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ fixSessionId, input }: { fixSessionId: string; input: FixActionRequest }) =>
      client.rereviewFixSession(fixSessionId, input),
    onSuccess: (session) => {
      storeFixSession(queryClient, session);
      void queryClient.invalidateQueries({ queryKey: ["fix-report", session.id] });
      void queryClient.invalidateQueries({ queryKey: ["findings"] });
      void queryClient.invalidateQueries({ queryKey: ["evidence"] });
      void queryClient.invalidateQueries({ queryKey: ["pull-request-diff"] });
      void queryClient.invalidateQueries({ queryKey: ["pull-request-graph"] });
    },
  });
}

export function useCancelFixSession() {
  const client = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ fixSessionId, input }: { fixSessionId: string; input: FixActionRequest }) =>
      client.cancelFixSession(fixSessionId, input),
    onSuccess: (session) => storeFixSession(queryClient, session),
  });
}

export function useRollbackFixSession() {
  const client = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ fixSessionId, input }: { fixSessionId: string; input: FixActionRequest }) =>
      client.rollbackFixSession(fixSessionId, input),
    onSuccess: (session) => {
      storeFixSession(queryClient, session);
      void queryClient.invalidateQueries({ queryKey: ["fix-patch", session.id] });
      void queryClient.invalidateQueries({ queryKey: ["fix-report", session.id] });
    },
  });
}

export function useDeleteFixWorkspace() {
  const client = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ fixSessionId, expectedLockVersion }: { fixSessionId: string; expectedLockVersion: number }) =>
      client.deleteFixWorkspace(fixSessionId, expectedLockVersion),
    onSuccess: (_result, variables) => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.fixSession(variables.fixSessionId) });
      void queryClient.invalidateQueries({ queryKey: ["fix-sessions"] });
    },
  });
}

export function useFixWorkspaces() {
  const client = useApiClient();
  return useQuery({
    queryKey: queryKeys.fixWorkspaces,
    queryFn: ({ signal }) => client.listFixWorkspaces(signal),
    retry: 1,
  });
}

export function useCleanupFixWorkspace() {
  const client = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ fixSessionId }: { fixSessionId: string }) =>
      client.cleanupFixWorkspace(fixSessionId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.fixWorkspaces });
      void queryClient.invalidateQueries({ queryKey: ["fix-sessions"] });
    },
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

export function useSetAgentEnabled() {
  const client = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ name, enabled }: { name: string; enabled: boolean }) =>
      client.setAgentEnabled(name, enabled),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: queryKeys.agents }),
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

export function useSetToolEnabled() {
  const client = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ name, enabled }: { name: string; enabled: boolean }) =>
      client.setToolEnabled(name, enabled),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: queryKeys.tools }),
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
