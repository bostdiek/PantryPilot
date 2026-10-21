const RECOVERY_KEY = 'pantrypilot-session-recovery';
const RECOVERY_MAX_AGE_MS = 2 * 60 * 60 * 1000;

interface RecoverableField {
  formIndex: number;
  fieldIndex: number;
  value: string;
  checked?: boolean;
}

interface RecoverySnapshot {
  path: string;
  capturedAt: number;
  fields: RecoverableField[];
  userId?: string;
  recipeDraft?: RecipeCreate;
}

let captureRecipeDraft: (() => RecipeCreate) | undefined;

/** Register the mounted recipe form's complete React state for expiry recovery. */
export function registerRecipeDraft(capture: () => RecipeCreate): () => void {
  captureRecipeDraft = capture;
  return () => {
    if (captureRecipeDraft === capture) captureRecipeDraft = undefined;
  };
}

function readSnapshot(path: string, userId?: string): RecoverySnapshot | null {
  try {
    const serialized = sessionStorage.getItem(RECOVERY_KEY);
    if (!serialized) return null;
    const snapshot = JSON.parse(serialized) as RecoverySnapshot;
    if (Date.now() - snapshot.capturedAt > RECOVERY_MAX_AGE_MS) {
      sessionStorage.removeItem(RECOVERY_KEY);
      return null;
    }
    return snapshot.path === path && snapshot.userId === userId
      ? snapshot
      : null;
  } catch (error) {
    logger.warn('Could not read saved session inputs', error);
    return null;
  }
}

function saveSnapshot(snapshot: RecoverySnapshot): void {
  try {
    if (snapshot.fields.length || snapshot.recipeDraft) {
      sessionStorage.setItem(RECOVERY_KEY, JSON.stringify(snapshot));
    } else {
      sessionStorage.removeItem(RECOVERY_KEY);
    }
  } catch (error) {
    logger.warn('Could not save session inputs', error);
  }
}

/** Consume the recipe draft only on its original route and for its original user. */
export function takeRecoveredRecipeDraft(
  path: string,
  userId?: string
): RecipeCreate | undefined {
  const snapshot = readSnapshot(path, userId);
  if (!snapshot?.recipeDraft) return undefined;
  const draft = snapshot.recipeDraft;
  delete snapshot.recipeDraft;
  saveSnapshot(snapshot);
  return draft;
}

type RecoverableControl =
  HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement;

function editableFields(form: HTMLFormElement): RecoverableControl[] {
  if (form.dataset.sessionRecovery === 'structured') return [];
  return Array.from(
    form.querySelectorAll<
      HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
    >('input, textarea, select')
  ).filter((field) => {
    if (field instanceof HTMLInputElement) {
      return !['password', 'file', 'hidden', 'submit', 'button'].includes(
        field.type
      );
    }
    return true;
  });
}

/** Save recoverable inputs in this tab, bound to the expiring account. */
export function captureSessionRecovery(userId?: string): void {
  if (
    typeof document === 'undefined' ||
    typeof window === 'undefined' ||
    typeof sessionStorage === 'undefined'
  ) {
    return;
  }

  const fields = Array.from(document.forms).flatMap((form, formIndex) =>
    editableFields(form).map((field, fieldIndex) => ({
      formIndex,
      fieldIndex,
      value:
        field instanceof HTMLInputElement &&
        ['checkbox', 'radio'].includes(field.type)
          ? ''
          : field.value,
      ...(field instanceof HTMLInputElement &&
      ['checkbox', 'radio'].includes(field.type)
        ? { checked: field.checked }
        : {}),
    }))
  );

  const recipeDraft = captureRecipeDraft?.();
  if (fields.length === 0 && !recipeDraft) return;
  const snapshot: RecoverySnapshot = {
    path: window.location.pathname + window.location.search,
    capturedAt: Date.now(),
    fields,
    userId,
    recipeDraft,
  };
  saveSnapshot(snapshot);
}

/** Restore native controls only after the original account signs in again. */
export function restoreSessionRecovery(path: string, userId?: string): void {
  if (
    typeof document === 'undefined' ||
    typeof window === 'undefined' ||
    typeof sessionStorage === 'undefined'
  ) {
    return;
  }

  const snapshot = readSnapshot(path, userId);
  if (!snapshot || snapshot.fields.length === 0) return;

  const restoredFields = new Set<string>();
  const clearRestoredFields = () => {
    const current = readSnapshot(path, userId);
    if (current?.capturedAt !== snapshot.capturedAt) return;
    current.fields = [];
    saveSnapshot(current);
  };
  const restore = () => {
    const forms = Array.from(document.forms);
    for (const field of snapshot.fields) {
      const fieldKey = `${field.formIndex}:${field.fieldIndex}`;
      if (restoredFields.has(fieldKey)) continue;
      const form = forms[field.formIndex];
      const element = form && editableFields(form)[field.fieldIndex];
      if (!element) continue;

      if (
        element instanceof HTMLInputElement &&
        typeof field.checked === 'boolean'
      ) {
        element.checked = field.checked;
        element.dispatchEvent(new Event('change', { bubbles: true }));
      } else if (
        element instanceof HTMLInputElement ||
        element instanceof HTMLTextAreaElement ||
        element instanceof HTMLSelectElement
      ) {
        const setter = Object.getOwnPropertyDescriptor(
          Object.getPrototypeOf(element),
          'value'
        )?.set;
        setter?.call(element, field.value);
        element.dispatchEvent(new Event('input', { bubbles: true }));
        element.dispatchEvent(new Event('change', { bubbles: true }));
      }
      restoredFields.add(fieldKey);
    }
    if (restoredFields.size === snapshot.fields.length) {
      clearRestoredFields();
      observer.disconnect();
      window.clearTimeout(timeout);
    }
  };

  const observer = new MutationObserver(restore);
  const timeout = window.setTimeout(() => {
    observer.disconnect();
    clearRestoredFields();
  }, 30_000);
  observer.observe(document.body, { childList: true, subtree: true });
  restore();
}
import type { RecipeCreate } from '../types/Recipe';
import { logger } from '../lib/logger';
