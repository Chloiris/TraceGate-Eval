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

export const credentialKindSchema = z.enum(["github", "model"]);
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
    eval: componentStatusSchema,
  }),
  checked_at: z.string().min(1),
});

export type SystemStatus = z.infer<typeof systemStatusSchema>;

export const themeSchema = z.enum(["system", "light", "dark"]);
export const languageSchema = z.enum(["zh-CN", "en-US"]);

export const settingsSchema = z.object({
  theme: themeSchema,
  language: languageSchema,
  background_monitoring: z.boolean(),
  launch_at_startup: z.boolean(),
  model_provider: z.string().nullable(),
  model_base_url: z.string().nullable(),
  model_name: z.string().nullable(),
  updated_at: z.string().min(1),
});

export type Settings = z.infer<typeof settingsSchema>;

export const settingsUpdateSchema = settingsSchema.pick({
  theme: true,
  language: true,
  background_monitoring: true,
  launch_at_startup: true,
});

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
