import { logger } from './logger';

export type ProductTelemetryEventName =
  | 'assistant_message_started'
  | 'assistant_message_completed'
  | 'assistant_message_failed'
  | 'assistant_tool_started'
  | 'assistant_tool_completed'
  | 'url_import_started'
  | 'url_import_stream_fallback'
  | 'url_import_completed'
  | 'url_import_failed'
  | 'image_import_started'
  | 'image_import_completed'
  | 'image_import_failed'
  | 'recipe_search_submitted'
  | 'recipe_search_result_clicked';

export type ProductTelemetryFeatureName =
  | 'assistant'
  | 'url_import'
  | 'image_import'
  | 'recipe_search';

export interface ProductTelemetryRequestMetadata {
  requestId: string;
  featureName: ProductTelemetryFeatureName;
  conversationId?: string;
}

export interface ProductTelemetryAttributes {
  feature_name?: ProductTelemetryFeatureName;
  trace_id?: string;
  request_id?: string;
  conversation_id?: string;
  provider?: string;
  model_name?: string;
  success?: boolean;
  latency_ms?: number;
  error_type?: string;
  tool_count?: number;
  tool_names?: string[];
  streamed?: boolean;
  cancelled?: boolean;
  file_count?: number;
  query_length?: number;
  result_count?: number;
  url_length?: number;
}

function createRequestId(): string {
  const generated = globalThis.crypto?.randomUUID?.();
  if (generated) {
    return generated;
  }

  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function compactAttributes(
  attrs: Record<string, unknown>
): Record<string, string | number | boolean | string[]> {
  return Object.fromEntries(
    Object.entries(attrs).filter(([, value]) => value !== undefined)
  ) as Record<string, string | number | boolean | string[]>;
}

export function createProductTelemetryRequestMetadata(
  input: Omit<ProductTelemetryRequestMetadata, 'requestId'> & {
    requestId?: string;
  }
): ProductTelemetryRequestMetadata {
  return {
    requestId: input.requestId ?? createRequestId(),
    featureName: input.featureName,
    conversationId: input.conversationId,
  };
}

export function buildTelemetryRequestHeaders(
  metadata?: ProductTelemetryRequestMetadata
): Record<string, string> {
  if (!metadata) {
    return {};
  }

  return {
    'X-Correlation-ID': metadata.requestId,
  };
}

export function getTelemetryLatencyMs(startedAtMs: number): number {
  return Math.max(0, Date.now() - startedAtMs);
}

export function classifyTelemetryError(error: unknown): string {
  if (!error || typeof error !== 'object') {
    return 'unknown_error';
  }

  const candidate = error as Record<string, unknown>;
  const explicitCode =
    (typeof candidate.code === 'string' && candidate.code) ||
    (typeof candidate.error_code === 'string' && candidate.error_code) ||
    (typeof candidate.type === 'string' && candidate.type);
  if (explicitCode) {
    return explicitCode;
  }

  if (typeof candidate.status === 'number') {
    return `http_${candidate.status}`;
  }

  if (error instanceof Error && error.name) {
    return error.name;
  }

  return 'unknown_error';
}

export function emitProductTelemetryEvent(
  eventName: ProductTelemetryEventName,
  metadata: ProductTelemetryRequestMetadata,
  attributes: ProductTelemetryAttributes = {}
): void {
  const payload = compactAttributes({
    event_name: eventName,
    request_id: metadata.requestId,
    feature_name: attributes.feature_name ?? metadata.featureName,
    conversation_id: attributes.conversation_id ?? metadata.conversationId,
    ...attributes,
  });

  logger.info('Product telemetry event', payload);
}
