import { z } from "zod";

export const componentStateSchema = z.enum([
  "ready",
  "not_configured",
  "error",
  "unavailable",
]);

export type ComponentState = z.infer<typeof componentStateSchema>;

export const componentStatusSchema = z.object({
  state: componentStateSchema,
  configured: z.boolean(),
  message: z.string().min(1),
  detail: z.string().nullable().optional(),
});

export type ComponentStatus = z.infer<typeof componentStatusSchema>;

export const apiConnectionSchema = z.object({
  baseUrl: z.string().min(1),
  token: z.string().min(1),
});

export type ApiConnection = z.infer<typeof apiConnectionSchema>;

export const credentialKindSchema = z.enum(["github", "model", "relay"]);
export type CredentialKind = z.infer<typeof credentialKindSchema>;

export const credentialStatusSchema = z.object({
  kind: credentialKindSchema,
  configured: z.boolean(),
  storage: z.string().min(1),
  restartRequiredAfterChange: z.boolean(),
});
export type CredentialStatus = z.infer<typeof credentialStatusSchema>;

export const healthResponseSchema = z.object({
  status: z.literal("ok"),
  service: z.literal("tracegate-studio"),
  version: z.string().min(1),
  api_version: z.literal("v1"),
  database: componentStatusSchema,
});

export type HealthResponse = z.infer<typeof healthResponseSchema>;

export const systemStatusSchema = z.object({
  status: z.enum(["ready", "degraded", "error"]),
  components: z.object({
    api: componentStatusSchema,
    database: componentStatusSchema,
    github: componentStatusSchema,
    model: componentStatusSchema,
    webhook_relay: componentStatusSchema,
    eval: componentStatusSchema,
  }),
  checked_at: z.string().min(1),
});

export type SystemStatus = z.infer<typeof systemStatusSchema>;

export const connectionComponentSchema = z.enum(["backend", "github", "model"]);
export const connectionTestResponseSchema = z.object({
  component: connectionComponentSchema,
  status: z.literal("ready"),
  message: z.string().min(1),
  detail: z.string().nullable(),
  latency_ms: z.number().int().nonnegative(),
});
export type ConnectionComponent = z.infer<typeof connectionComponentSchema>;
export type ConnectionTestResponse = z.infer<typeof connectionTestResponseSchema>;

export const themeSchema = z.enum(["system", "light", "dark"]);
export const languageSchema = z.enum(["zh-CN", "en-US"]);

export const settingsSchema = z.object({
  theme: themeSchema,
  language: languageSchema,
  background_monitoring: z.boolean(),
  launch_at_startup: z.boolean(),
  close_notice_dismissed: z.boolean(),
  notifications_enabled: z.boolean(),
  model_provider: z.string().nullable(),
  model_base_url: z.string().nullable(),
  model_name: z.string().nullable(),
  model_temperature: z.number().min(0).max(2),
  model_max_output_tokens: z.number().int().min(256).max(32768),
  model_timeout_seconds: z.number().int().min(5).max(300),
  model_max_retries: z.number().int().min(0).max(3),
  model_native_structured_output: z.boolean(),
  model_streaming_enabled: z.boolean(),
  model_native_tool_calling: z.boolean(),
  model_context_scope: z.enum(["changed_files", "retrieved_context"]),
  model_input_cost_per_million: z.number().min(0).max(10000),
  model_output_cost_per_million: z.number().min(0).max(10000),
  github_poll_interval_seconds: z.number().int().min(30).max(3600),
  automatic_analysis_enabled: z.boolean(),
  automatic_analysis_include_drafts: z.boolean(),
  automatic_analysis_require_checks_success: z.boolean(),
  analysis_paused: z.boolean(),
  webhook_relay_url: z.string().url().nullable(),
  webhook_relay_device_id: z.string().nullable(),
  updated_at: z.string().min(1),
});

export type Settings = z.infer<typeof settingsSchema>;

export const settingsUpdateSchema = settingsSchema
  .pick({
    theme: true,
    language: true,
    background_monitoring: true,
    launch_at_startup: true,
    close_notice_dismissed: true,
    notifications_enabled: true,
    model_provider: true,
    model_base_url: true,
    model_name: true,
    model_temperature: true,
    model_max_output_tokens: true,
    model_timeout_seconds: true,
    model_max_retries: true,
    model_native_structured_output: true,
    model_streaming_enabled: true,
    model_native_tool_calling: true,
    model_context_scope: true,
    model_input_cost_per_million: true,
    model_output_cost_per_million: true,
    github_poll_interval_seconds: true,
    automatic_analysis_enabled: true,
    automatic_analysis_include_drafts: true,
    automatic_analysis_require_checks_success: true,
    analysis_paused: true,
    webhook_relay_url: true,
    webhook_relay_device_id: true,
  })
  .partial()
  .refine((value) => Object.keys(value).length > 0, "At least one setting is required");

export type SettingsUpdate = z.infer<typeof settingsUpdateSchema>;

export const onboardingStepSchema = z.enum([
  "welcome",
  "appearance",
  "github",
  "model",
  "repository",
  "background",
  "complete",
]);

export type OnboardingStep = z.infer<typeof onboardingStepSchema>;

export const onboardingStateSchema = z.object({
  completed: z.boolean(),
  current_step: onboardingStepSchema,
  github: componentStatusSchema,
  model: componentStatusSchema,
  webhook_relay: componentStatusSchema,
  repository_added: z.boolean(),
  background_monitoring: z.boolean(),
  launch_at_startup: z.boolean(),
  completed_at: z.string().nullable(),
  updated_at: z.string().min(1),
});

export type OnboardingState = z.infer<typeof onboardingStateSchema>;

export const onboardingUpdateSchema = z.object({
  completed: z.boolean(),
  current_step: onboardingStepSchema,
  background_monitoring: z.boolean(),
  launch_at_startup: z.boolean(),
});

export type OnboardingUpdate = z.infer<typeof onboardingUpdateSchema>;

export const errorEnvelopeSchema = z.object({
  error: z.object({
    code: z.string().min(1),
    message: z.string().min(1),
  }),
});

export type ErrorEnvelope = z.infer<typeof errorEnvelopeSchema>;

export function isComponentReady(status: ComponentStatus): boolean {
  return status.state === "ready" && status.configured;
}

const isoDateSchema = z.string().min(1);

export const repositorySchema = z.object({
  id: z.string().uuid(),
  owner: z.string().min(1),
  name: z.string().min(1),
  full_name: z.string().min(3),
  clone_url: z.string().nullable(),
  local_path: z.string().nullable(),
  default_branch: z.string().nullable(),
  monitoring_enabled: z.boolean(),
  connection_status: z.enum(["not_connected", "pending", "ready", "error"]),
  last_error: z.string().nullable(),
  current_commit_sha: z.string().nullable(),
  current_index_version: z.string().nullable(),
  last_synced_at: isoDateSchema.nullable(),
  github_rate_remaining: z.number().int().nullable(),
  created_at: isoDateSchema,
  updated_at: isoDateSchema,
});
export type Repository = z.infer<typeof repositorySchema>;

export const repositoryCreateSchema = z.object({
  full_name: z.string().regex(/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/),
  local_path: z.string().min(1).nullable().optional(),
  monitoring_enabled: z.boolean().default(false),
});
export type RepositoryCreate = z.input<typeof repositoryCreateSchema>;

export const repositoryUpdateSchema = z.object({
  local_path: z.string().min(1).nullable().optional(),
  default_branch: z.string().min(1).nullable().optional(),
  monitoring_enabled: z.boolean().optional(),
}).refine((value) => Object.keys(value).length > 0, "At least one repository field is required");
export type RepositoryUpdate = z.infer<typeof repositoryUpdateSchema>;

export const repositoryListSchema = z.object({
  items: z.array(repositorySchema),
  total: z.number().int().nonnegative(),
  limit: z.number().int().positive(),
  offset: z.number().int().nonnegative(),
});
export type RepositoryList = z.infer<typeof repositoryListSchema>;

export const repositorySummarySchema = z.object({
  repository_id: z.string().uuid(),
  commit_sha: z.string().nullable(),
  index_version: z.string().uuid().nullable(),
  file_count: z.number().int().nonnegative(),
  directory_count: z.number().int().nonnegative(),
  symbol_count: z.number().int().nonnegative(),
  dependency_edge_count: z.number().int().nonnegative(),
  language_counts: z.record(z.string(), z.number().int().nonnegative()),
  active_pull_requests: z.number().int().nonnegative(),
});
export type RepositorySummary = z.infer<typeof repositorySummarySchema>;

export const repositorySyncSchema = z.object({
  sync_id: z.string().uuid(),
  status: z.enum(["completed", "not_modified", "failed"]),
  changed_pull_requests: z.number().int().nonnegative(),
  changed_check_runs: z.number().int().nonnegative(),
  etag: z.string().nullable(),
  github_rate_remaining: z.number().int().nullable(),
  finished_at: isoDateSchema,
});
export type RepositorySync = z.infer<typeof repositorySyncSchema>;

export const indexVersionSchema = z.object({
  id: z.string().uuid(),
  repository_id: z.string().uuid(),
  commit_sha: z.string().min(7),
  status: z.string().min(1),
  file_count: z.number().int().nonnegative(),
  symbol_count: z.number().int().nonnegative(),
  changed_count: z.number().int().nonnegative(),
  deleted_count: z.number().int().nonnegative(),
  duration_ms: z.number().int().nonnegative(),
  index_duration_ms: z.number().int().nonnegative(),
  graph_duration_ms: z.number().int().nonnegative(),
  created_at: isoDateSchema,
});
export type IndexVersion = z.infer<typeof indexVersionSchema>;

const graphNodeBase = z.object({
  id: z.string().min(1),
  label: z.string().min(1),
  path: z.string().min(1),
  language: z.string().nullable(),
});

export const graphNodeSchema = graphNodeBase.extend({
  kind: z.enum(["repository", "directory", "file", "test", "class", "interface", "function", "method", "api_route", "database_entity"]),
  symbol: z.string().min(1).nullable(),
});
export type GraphNode = z.infer<typeof graphNodeSchema>;

export const graphEdgeSchema = z.object({
  id: z.string().min(1),
  source: z.string().min(1),
  target: z.string().min(1),
  kind: z.enum(["contains", "import", "export", "call", "inherit", "implement", "reference", "route", "database", "test", "config", "changed-with"]),
  confirmed: z.boolean(),
});
export type GraphEdge = z.infer<typeof graphEdgeSchema>;

export const repositoryGraphSchema = z.object({
  repository_id: z.string().uuid(),
  commit_sha: z.string().min(7),
  index_version: z.string().uuid(),
  nodes: z.array(graphNodeSchema),
  edges: z.array(graphEdgeSchema),
  vector_search_enabled: z.literal(false),
  vector_search_message: z.string().min(1),
});
export type RepositoryGraph = z.infer<typeof repositoryGraphSchema>;

export const pullRequestSchema = z.object({
  id: z.string().uuid(),
  repository_id: z.string().uuid(),
  number: z.number().int().positive(),
  title: z.string().min(1),
  state: z.string().min(1),
  url: z.string().url(),
  author: z.string().nullable(),
  base_ref: z.string().nullable(),
  head_ref: z.string().nullable(),
  base_sha: z.string().nullable(),
  head_sha: z.string().nullable(),
  draft: z.boolean(),
  additions: z.number().int().nonnegative(),
  deletions: z.number().int().nonnegative(),
  changed_files: z.number().int().nonnegative(),
  analysis_status: z.string().min(1),
  checks_status: z.enum(["not_available", "pending", "success", "failure", "neutral"]),
  last_checks_synced_at: isoDateSchema.nullable(),
  risk_level: z.enum(["info", "low", "medium", "high", "critical"]).nullable(),
  risk_score: z.number().min(0).max(100).nullable(),
  conclusion_summary: z.string().nullable(),
  impact_paths_json: z.array(z.string()),
  recommended_review_order_json: z.array(z.string()),
  latest_model_profile: z.string().nullable(),
  updated_at_github: isoDateSchema.nullable(),
  created_at: isoDateSchema,
  updated_at: isoDateSchema,
});
export type PullRequest = z.infer<typeof pullRequestSchema>;

export const pullRequestListSchema = z.object({
  items: z.array(pullRequestSchema),
  total: z.number().int().nonnegative(),
  limit: z.number().int().positive(),
  offset: z.number().int().nonnegative(),
});
export type PullRequestList = z.infer<typeof pullRequestListSchema>;

export const checkRunSchema = z.object({
  id: z.string().uuid(),
  github_id: z.number().int().positive(),
  pull_request_id: z.string().uuid(),
  head_sha: z.string().min(7),
  name: z.string().min(1),
  status: z.string().min(1),
  conclusion: z.string().nullable(),
  details_url: z.string().url().nullable(),
  app_name: z.string().nullable(),
  started_at: isoDateSchema.nullable(),
  completed_at: isoDateSchema.nullable(),
  synced_at: isoDateSchema,
});
export type CheckRun = z.infer<typeof checkRunSchema>;

export const checkRunListSchema = z.object({
  items: z.array(checkRunSchema),
  aggregate_status: z.enum(["not_available", "pending", "success", "failure", "neutral"]),
  synced_at: isoDateSchema.nullable(),
});
export type CheckRunList = z.infer<typeof checkRunListSchema>;

export const pullRequestCommitSchema = z.object({
  id: z.string().uuid(),
  pull_request_id: z.string().uuid(),
  sha: z.string().min(7),
  message: z.string(),
  author_name: z.string().nullable(),
  author_email: z.string().nullable(),
  author_login: z.string().nullable(),
  authored_at: isoDateSchema.nullable(),
  html_url: z.string().url().nullable(),
  position: z.number().int().positive(),
  synced_at: isoDateSchema,
});
export type PullRequestCommit = z.infer<typeof pullRequestCommitSchema>;
export const pullRequestCommitListSchema = z.array(pullRequestCommitSchema);

export const changedHunkSchema = z.object({
  id: z.string().uuid(),
  sequence: z.number().int().positive(),
  header: z.string().min(1),
  old_start: z.number().int().nonnegative(),
  old_count: z.number().int().nonnegative(),
  new_start: z.number().int().nonnegative(),
  new_count: z.number().int().nonnegative(),
  patch: z.string().min(1),
  patch_hash: z.string().regex(/^[a-f0-9]{64}$/),
});
export type ChangedHunk = z.infer<typeof changedHunkSchema>;

export const changedFileDetailSchema = z.object({
  id: z.string().uuid(),
  pull_request_id: z.string().uuid(),
  head_sha: z.string().min(7),
  blob_sha: z.string().min(7),
  path: z.string().min(1),
  previous_path: z.string().nullable(),
  status: z.string().min(1),
  additions: z.number().int().nonnegative(),
  deletions: z.number().int().nonnegative(),
  changes: z.number().int().nonnegative(),
  blob_url: z.string().url().nullable(),
  raw_url: z.string().url().nullable(),
  contents_url: z.string().url().nullable(),
  patch_hash: z.string().regex(/^[a-f0-9]{64}$/).nullable(),
  synced_at: isoDateSchema,
  hunks: z.array(changedHunkSchema),
});
export type ChangedFileDetail = z.infer<typeof changedFileDetailSchema>;
export const changedFileDetailListSchema = z.array(changedFileDetailSchema);

export const pullRequestDiffSchema = z.object({
  pull_request_id: z.string().uuid(),
  base_sha: z.string().min(7),
  head_sha: z.string().min(7),
  changed_files: z.array(z.object({ path: z.string().min(1), status: z.string().min(1) })),
  selected_path: z.string().nullable(),
  original: z.string().nullable(),
  modified: z.string().nullable(),
  unified_diff: z.string(),
});
export type PullRequestDiff = z.infer<typeof pullRequestDiffSchema>;

export const agentRunSchema = z.object({
  id: z.string().uuid(),
  repository_id: z.string().uuid(),
  pull_request_id: z.string().uuid().nullable(),
  status: z.enum(["queued", "running", "completed", "failed", "cancelled"]),
  current_node: z.string().nullable(),
  head_sha: z.string().nullable(),
  prompt_version: z.string().nullable(),
  index_version: z.string().nullable(),
  workflow_version: z.string().nullable(),
  model_profile: z.string().nullable(),
  model_profile_id: z.string().uuid().nullable().default(null),
  context_scope: z.enum(["changed_files", "retrieved_context"]),
  input_tokens: z.number().int().nonnegative(),
  output_tokens: z.number().int().nonnegative(),
  latency_ms: z.number().int().nonnegative(),
  retry_count: z.number().int().nonnegative(),
  retrieval_hit_count: z.number().int().nonnegative(),
  cancellation_requested: z.boolean(),
  error_code: z.string().nullable(),
  error_message: z.string().nullable(),
  started_at: isoDateSchema.nullable(),
  finished_at: isoDateSchema.nullable(),
  created_at: isoDateSchema,
  updated_at: isoDateSchema,
});
export type AgentRun = z.infer<typeof agentRunSchema>;

export const agentRunListSchema = z.object({
  items: z.array(agentRunSchema),
  total: z.number().int().nonnegative(),
  limit: z.number().int().positive(),
  offset: z.number().int().nonnegative(),
});
export type AgentRunList = z.infer<typeof agentRunListSchema>;

export const analyzeResponseSchema = z.object({ run: agentRunSchema, reused: z.boolean() });
export type AnalyzeResponse = z.infer<typeof analyzeResponseSchema>;

export const agentStepSchema = z.object({
  id: z.string().uuid(),
  agent_run_id: z.string().uuid(),
  sequence: z.number().int().positive(),
  node: z.string().min(1),
  status: z.string().min(1),
  input_summary: z.string().nullable(),
  output_summary: z.string().nullable(),
  error_code: z.string().nullable(),
  error_message: z.string().nullable(),
  started_at: isoDateSchema,
  finished_at: isoDateSchema.nullable(),
  duration_ms: z.number().int().nonnegative().nullable(),
});
export type AgentStep = z.infer<typeof agentStepSchema>;

export const toolCallSchema = z.object({
  id: z.string().uuid(),
  agent_step_id: z.string().uuid(),
  tool_name: z.string().min(1),
  permission: z.enum([
    "SAFE_READ",
    "REPOSITORY_READ",
    "COMMAND_RESTRICTED",
    "WRITE_CONFIRMATION",
    "NETWORK",
    "DESTRUCTIVE_FORBIDDEN",
  ]),
  arguments_summary: z.string(),
  output_summary: z.string().nullable(),
  status: z.string().min(1),
  duration_ms: z.number().int().nonnegative().nullable(),
  error_code: z.string().nullable(),
});
export type ToolCall = z.infer<typeof toolCallSchema>;

export const agentRunDetailSchema = agentRunSchema.extend({
  steps: z.array(agentStepSchema),
  tool_calls: z.array(toolCallSchema),
});
export type AgentRunDetail = z.infer<typeof agentRunDetailSchema>;

export const findingSchema = z.object({
  id: z.string().uuid(),
  agent_run_id: z.string().uuid(),
  severity: z.string().min(1),
  confidence: z.number().min(0).max(1),
  category: z.string().min(1),
  title: z.string().min(1),
  message: z.string().min(1),
  file_path: z.string().nullable(),
  line_start: z.number().int().positive().nullable(),
  line_end: z.number().int().positive().nullable(),
  commit_sha: z.string().nullable(),
  symbol: z.string().nullable(),
  evidence_ids_json: z.array(z.string()),
  suggested_action: z.string().nullable(),
  verifier_status: z.string().min(1),
  model_profile: z.string().nullable(),
  created_at: isoDateSchema,
});
export type Finding = z.infer<typeof findingSchema>;

export const evidenceSchema = z.object({
  id: z.string().min(1),
  agent_run_id: z.string().uuid(),
  source_type: z.string().min(1),
  source_uri: z.string().min(1),
  file_path: z.string().nullable(),
  commit_sha: z.string().nullable(),
  content_hash: z.string().min(1),
  payload_json: z.record(z.string(), z.unknown()),
  created_at: isoDateSchema,
});
export type Evidence = z.infer<typeof evidenceSchema>;

export const notificationKindSchema = z.enum([
  "new_pull_request",
  "new_pull_request_commit",
  "analysis_started",
  "high_risk_finding",
  "analysis_completed",
  "analysis_failed",
  "github_authentication_failed",
  "sidecar_restart_failed",
  "test",
]);
export const notificationCreateSchema = z.object({
  kind: notificationKindSchema,
  status: z.enum(["delivered", "failed"]),
  title: z.string().min(1).max(500),
  body: z.string().min(1).max(4000),
  deep_link: z.string().startsWith("tracegate://").nullable().optional(),
  repository_id: z.string().uuid().nullable().optional(),
  pull_request_id: z.string().uuid().nullable().optional(),
  agent_run_id: z.string().uuid().nullable().optional(),
  error_message: z.string().max(4000).nullable().optional(),
});
export type NotificationCreate = z.infer<typeof notificationCreateSchema>;
export const notificationRecordSchema = notificationCreateSchema.extend({
  id: z.string().uuid(),
  deep_link: z.string().startsWith("tracegate://").nullable(),
  repository_id: z.string().uuid().nullable(),
  pull_request_id: z.string().uuid().nullable(),
  agent_run_id: z.string().uuid().nullable(),
  error_message: z.string().nullable(),
  attempted_at: isoDateSchema,
});
export type NotificationRecord = z.infer<typeof notificationRecordSchema>;

export const evaluationArtifactSchema = z.object({
  path: z.string().min(1),
  sha256: z.string().regex(/^[a-f0-9]{64}$/),
});

export const evaluationCaseSchema = z.object({
  model: z.string().min(1),
  task_id: z.string().min(1),
  evidence_status: z.string().min(1),
  expected_decision: z.string().min(1),
  decision: z.string().min(1),
  context_group: z.string().min(1),
  claimbench_status: z.string().min(1),
  safe_success: z.boolean(),
  evidence_aware_decision: z.boolean(),
  context_tokens: z.number().int().nonnegative(),
  run_dir: z.string().min(1),
});
export type EvaluationCase = z.infer<typeof evaluationCaseSchema>;

const integerDistributionSchema = z.record(z.string(), z.number().int().nonnegative());
export const evaluationSummarySchema = z.object({
  benchmark_name: z.string().min(1),
  benchmark_note: z.string().min(1),
  dataset_sha256: z.string().regex(/^[a-f0-9]{64}$/),
  is_real_dataset: z.literal(true),
  case_count: z.number().int().positive(),
  claimbench_run_count: z.number().int().positive(),
  status_distribution: integerDistributionSchema,
  risk_distribution: integerDistributionSchema,
  decision_distribution: integerDistributionSchema,
  metrics: z.record(z.string(), z.number()),
  models: integerDistributionSchema,
  context_groups: integerDistributionSchema,
  claimbench_status_distribution: integerDistributionSchema,
  claimbench_decision_distribution: integerDistributionSchema,
  limitations: z.array(z.string().min(1)),
  artifacts: z.array(evaluationArtifactSchema).min(1),
  cases: z.array(evaluationCaseSchema).min(1),
});
export type EvaluationSummary = z.infer<typeof evaluationSummarySchema>;

export const agentDescriptorSchema = z.object({
  name: z.string().min(1),
  version: z.string().min(1),
  responsibility: z.string().min(1),
  status: z.enum(["enabled", "disabled"]),
  capabilities: z.array(z.string().min(1)),
  allowed_tools: z.array(z.string().min(1)),
});
export type AgentDescriptor = z.infer<typeof agentDescriptorSchema>;
export const agentDescriptorListSchema = z.array(agentDescriptorSchema);

export const permissionLevelSchema = z.enum([
  "SAFE_READ",
  "REPOSITORY_READ",
  "COMMAND_RESTRICTED",
  "WRITE_CONFIRMATION",
  "NETWORK",
  "DESTRUCTIVE_FORBIDDEN",
]);

export const toolDescriptorSchema = z.object({
  name: z.string().min(1),
  description: z.string().min(1),
  permission: permissionLevelSchema,
  timeout_seconds: z.number().positive(),
  max_output_bytes: z.number().int().positive(),
  input_schema: z.record(z.string(), z.unknown()),
  enabled: z.boolean(),
  recent_call_count: z.number().int().nonnegative(),
  recent_error_count: z.number().int().nonnegative(),
  most_recent_error: z.string().nullable(),
});
export type ToolDescriptor = z.infer<typeof toolDescriptorSchema>;
export const toolDescriptorListSchema = z.array(toolDescriptorSchema);
export const registryToggleSchema = z.object({ enabled: z.boolean() });
export type RegistryToggle = z.infer<typeof registryToggleSchema>;

export const reviewMapNodeSchema = z.object({
  id: z.string().min(1),
  kind: z.string().min(1),
  label: z.string().min(1),
  path: z.string().nullable(),
  symbol: z.string().nullable(),
  language: z.string().nullable(),
  impact_depth: z.number().int().min(0).max(2),
  change_status: z.enum(["added", "modified", "deleted", "renamed"]).nullable(),
  risk: z.enum(["info", "low", "medium", "high", "critical"]).nullable(),
  finding_ids: z.array(z.string()),
  evidence_ids: z.array(z.string()),
});
export type ReviewMapNode = z.infer<typeof reviewMapNodeSchema>;

export const reviewMapSchema = z.object({
  pull_request_id: z.string().uuid(),
  base_sha: z.string().min(7),
  head_sha: z.string().min(7),
  index_version: z.string().uuid(),
  source: z.literal("git_diff+static_index+agent_evidence"),
  nodes: z.array(reviewMapNodeSchema),
  edges: z.array(z.object({
    id: z.string().min(1),
    source: z.string().min(1),
    target: z.string().min(1),
    kind: z.string().min(1),
    confirmed: z.boolean(),
  })),
  truncated: z.boolean(),
  message: z.string().min(1),
});
export type ReviewMap = z.infer<typeof reviewMapSchema>;

export const changeTourSchema = z.object({
  pull_request_id: z.string().uuid(),
  head_sha: z.string().min(7),
  source: z.literal("git_diff+static_index+agent_evidence"),
  complete: z.boolean(),
  message: z.string().min(1),
  steps: z.array(z.object({
    sequence: z.number().int().positive(),
    title: z.string().min(1),
    files: z.array(z.string().min(1)).min(1),
    symbols: z.array(z.string().min(1)),
    purpose: z.string().min(1),
    prerequisite_step: z.number().int().positive().nullable(),
    risk: z.string().nullable(),
    evidence_ids: z.array(z.string()),
    checkpoints: z.array(z.string().min(1)),
    confidence: z.enum(["high", "medium", "low"]),
  })),
});
export type ChangeTour = z.infer<typeof changeTourSchema>;

export const diagnosticsSchema = z.object({
  software_version: z.string().min(1),
  git_commit: z.string().nullable(),
  operating_system: z.string().min(1),
  architecture: z.string().min(1),
  python_version: z.string().min(1),
  frontend_version: z.string().nullable(),
  desktop_version: z.string().nullable(),
  rust_version_info: z.string().nullable(),
  log_level: z.string().min(1),
  database_type: z.string().min(1),
  database_path: z.string().nullable(),
  log_path: z.string().min(1),
  workspace_paths: z.array(z.string().min(1)),
  sidecar_pid: z.number().int().positive(),
  api_port: z.number().int().positive(),
  github: componentStatusSchema,
  model: componentStatusSchema,
  webhook_relay: componentStatusSchema,
  monitor: z.object({
    running: z.boolean(),
    polling: z.boolean(),
    queued_repositories: z.number().int().nonnegative(),
    last_started_at: isoDateSchema.nullable(),
    last_finished_at: isoDateSchema.nullable(),
    last_error: z.string().nullable(),
    rate_limited_until: isoDateSchema.nullable(),
  }),
  relay_monitor: z.object({
    running: z.boolean(),
    connected: z.boolean(),
    reconnect_count: z.number().int().nonnegative(),
    last_connected_at: isoDateSchema.nullable(),
    last_event_at: isoDateSchema.nullable(),
    last_repository: z.string().nullable(),
    last_error: z.string().nullable(),
  }),
  agent_queue: z.number().int().nonnegative(),
  index_queue: z.number().int().nonnegative(),
  last_github_api_request_count: z.number().int().nonnegative().nullable(),
  last_github_api_duration_ms: z.number().int().nonnegative().nullable(),
  last_index_duration_ms: z.number().int().nonnegative().nullable(),
  last_graph_duration_ms: z.number().int().nonnegative().nullable(),
  last_retrieval_result_count: z.number().int().nonnegative().nullable(),
  last_model_latency_ms: z.number().int().nonnegative().nullable(),
  last_model_input_tokens: z.number().int().nonnegative().nullable(),
  last_model_output_tokens: z.number().int().nonnegative().nullable(),
  last_model_retry_count: z.number().int().nonnegative().nullable(),
  delivered_notification_count: z.number().int().nonnegative(),
  failed_notification_count: z.number().int().nonnegative(),
  telemetry_enabled: z.literal(false),
});
export type Diagnostics = z.infer<typeof diagnosticsSchema>;

export const agentEvidenceGraphSchema = z.object({
  run_id: z.string().uuid(),
  head_sha: z.string().nullable(),
  nodes: z.array(z.object({
    id: z.string().min(1),
    kind: z.string().min(1),
    label: z.string().min(1),
    detail: z.string().nullable(),
    status: z.string().nullable(),
    path: z.string().nullable(),
    line: z.number().int().positive().nullable(),
    commit_sha: z.string().nullable(),
    confidence: z.number().min(0).max(1).nullable(),
  })),
  edges: z.array(z.object({
    id: z.string().min(1),
    source: z.string().min(1),
    target: z.string().min(1),
    kind: z.string().min(1),
    confirmed: z.boolean(),
  })),
  message: z.string().min(1),
});
export type AgentEvidenceGraph = z.infer<typeof agentEvidenceGraphSchema>;

export const updateStatusSchema = z.object({
  current_version: z.string().min(1),
  channel: z.literal("stable"),
  configured: z.boolean(),
  update_available: z.boolean(),
  latest_version: z.string().nullable(),
  manifest_url: z.string().nullable(),
  signature_verification: z.boolean(),
  message: z.string().min(1),
});
export type UpdateStatus = z.infer<typeof updateStatusSchema>;
