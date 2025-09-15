/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL?: string;
  readonly VITE_API_HEALTH_TIMEOUT_MS?: string; // optional override for health check timeout (ms)
  readonly MODE: string; // Provided by Vite typing, redeclared for clarity
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
