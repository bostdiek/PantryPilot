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
}

type RecoverableControl =
  | HTMLInputElement
  | HTMLTextAreaElement
  | HTMLSelectElement;

function editableFields(form: HTMLFormElement): RecoverableControl[] {
  return Array.from(
    form.querySelectorAll<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>(
      'input, textarea, select'
    )
  ).filter((field) => {
    if (field instanceof HTMLInputElement) {
      return !['password', 'file', 'hidden', 'submit', 'button'].includes(
        field.type
      );
    }
    return true;
  });
}

export function captureSessionRecovery(): void {
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
        field instanceof HTMLInputElement && ['checkbox', 'radio'].includes(field.type)
          ? ''
          : field.value,
      ...(field instanceof HTMLInputElement &&
      ['checkbox', 'radio'].includes(field.type)
        ? { checked: field.checked }
        : {}),
    }))
  );

  if (fields.length === 0) return;
  const snapshot: RecoverySnapshot = {
    path: window.location.pathname + window.location.search,
    capturedAt: Date.now(),
    fields,
  };
  try {
    sessionStorage.setItem(RECOVERY_KEY, JSON.stringify(snapshot));
  } catch {
    return;
  }
}

export function restoreSessionRecovery(path: string): void {
  if (
    typeof document === 'undefined' ||
    typeof window === 'undefined' ||
    typeof sessionStorage === 'undefined'
  ) {
    return;
  }

  const serialized = sessionStorage.getItem(RECOVERY_KEY);
  if (!serialized) return;

  let snapshot: RecoverySnapshot;
  try {
    snapshot = JSON.parse(serialized) as RecoverySnapshot;
  } catch {
    sessionStorage.removeItem(RECOVERY_KEY);
    return;
  }
  if (
    snapshot.path !== path ||
    Date.now() - snapshot.capturedAt > RECOVERY_MAX_AGE_MS
  ) {
    return;
  }

  const restoredFields = new Set<string>();
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
      sessionStorage.removeItem(RECOVERY_KEY);
      observer.disconnect();
      window.clearTimeout(timeout);
    }
  };

  const observer = new MutationObserver(restore);
  const timeout = window.setTimeout(() => {
    observer.disconnect();
    sessionStorage.removeItem(RECOVERY_KEY);
  }, 30_000);
  observer.observe(document.body, { childList: true, subtree: true });
  restore();
}
