/**
 * Memory document response from backend.
 * Represents what Nibble remembers about the user.
 */
export interface MemoryDocument {
  content: string;
  format: 'markdown';
  version: number;
  updated_at: string;
  updated_by: 'assistant' | 'user';
}

/**
 * Request body for updating memory document.
 */
export interface MemoryUpdate {
  content: string;
}
