import type { RecipeCreate } from './Recipe';

/**
 * AI Draft types for recipe extraction from URLs
 * These types match the backend schemas defined in apps/backend/src/schemas/ai.py
 */

/**
 * AI-generated recipe data that follows RecipeCreate schema with metadata
 */
export interface AIGeneratedRecipe {
  recipe_data: RecipeCreate;
  confidence_score: number;
  extraction_notes: string | null;
  source_url: string;
}

/**
 * Extraction failure metadata
 */
export interface ExtractionFailure {
  reason: string;
}

/**
 * Metadata about the extraction process
 */
export interface ExtractionMetadata {
  confidence_score?: number;
  source_url: string;
  extracted_at: string;
  failure?: ExtractionFailure;
}

/**
 * AI Draft payload structure containing the extracted recipe or failure info
 */
export interface AIDraftPayload {
  generated_recipe: AIGeneratedRecipe | null;
  extraction_metadata: ExtractionMetadata;
}

/**
 * Response from fetching an AI draft
 */
export interface AIDraftFetchResponse {
  payload: AIDraftPayload;
  type: 'recipe_suggestion';
  created_at: string;
  expires_at: string;
}

/**
 * Response from creating/extracting a recipe from URL
 */
export interface AIDraftResponse {
  draft_id: string;
  signed_url: string;
  expires_at: string;
  ttl_seconds: number;
}

/**
 * SSE Event types for streaming extraction
 */
export type SSEEventStatus =
  | 'started'
  | 'fetching'
  | 'ai_call'
  | 'converting'
  | 'complete'
  | 'error';

export interface SSEEvent {
  status: SSEEventStatus;
  step: string;
  progress?: number;
  detail?: string;
  draft_id?: string;
  signed_url?: string;
  success?: boolean;
  confidence_score?: number;
  error_code?: string;
}
