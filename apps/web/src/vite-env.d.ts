/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_TRACEGATE_API_BASE_URL?: string;
  readonly VITE_TRACEGATE_API_TOKEN?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
