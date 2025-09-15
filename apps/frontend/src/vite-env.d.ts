/// <reference types="vite/client" />

interface ImportMetaEnv {
	readonly VITE_API_URL?: string;
	readonly MODE: string; // Provided by Vite typing, redeclared for clarity
}

interface ImportMeta {
	readonly env: ImportMetaEnv;
}
