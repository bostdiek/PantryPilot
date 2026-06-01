export type MealProposalPhase =
  | 'pending'
  | 'saving_recipe'
  | 'recipe_saved'
  | 'adding_to_plan'
  | 'retryable_add_failure'
  | 'added_to_plan'
  | 'rejected';

export type MealProposalReturnContext = {
  proposalKey?: string;
  returnToAssistant?: string;
  chatConversationId?: string;
  mealPlanDate?: string;
  mealPlanDayLabel?: string;
};

type PersistedMealProposalStatus = {
  version: 1;
  phase: MealProposalPhase;
  updatedAt?: string;
  proposalInstanceId?: string;
  recipeId?: string;
  returnContext?: MealProposalReturnContext;
  lastError?: string;
};

export type MealProposalStatus = PersistedMealProposalStatus & {
  savedToBook: boolean;
  addedToPlan: boolean;
  rejected: boolean;
  canRetryAdd: boolean;
};

export type MealProposalStatusUpdate = Omit<
  PersistedMealProposalStatus,
  'updatedAt' | 'version'
>;

export function getMealProposalInstanceId(proposalKey: string): string {
  const [proposalInstanceId] = proposalKey.split('|');
  return proposalInstanceId || proposalKey;
}

const KEY_PREFIX = 'pantrypilot_meal_proposal';
const STATUS_KEY_SUFFIX = 'status';
const STATUS_VERSION = 1 as const;
const PHASES: ReadonlySet<MealProposalPhase> = new Set([
  'pending',
  'saving_recipe',
  'recipe_saved',
  'adding_to_plan',
  'retryable_add_failure',
  'added_to_plan',
  'rejected',
]);
const LEGACY_STATUS_KEYS = ['savedToBook', 'addedToPlan', 'rejected'] as const;

type LegacyMealProposalStatusKey = (typeof LEGACY_STATUS_KEYS)[number];

function statusStorageKey(proposalKey: string): string {
  return `${KEY_PREFIX}:${proposalKey}:${STATUS_KEY_SUFFIX}`;
}

function legacyStorageKey(
  proposalKey: string,
  statusKey: LegacyMealProposalStatusKey
): string {
  return `${KEY_PREFIX}:${proposalKey}:${statusKey}`;
}

function readStorageItem(storageKey: string): string | null {
  try {
    return localStorage.getItem(storageKey);
  } catch {
    return null;
  }
}

function writeStorageItem(storageKey: string, value: string): void {
  try {
    localStorage.setItem(storageKey, value);
  } catch {
    // localStorage might be unavailable (privacy mode, etc.)
  }
}

function removeStorageItem(storageKey: string): void {
  try {
    localStorage.removeItem(storageKey);
  } catch {
    // localStorage might be unavailable (privacy mode, etc.)
  }
}

function isMealProposalPhase(value: unknown): value is MealProposalPhase {
  return typeof value === 'string' && PHASES.has(value as MealProposalPhase);
}

function readPersistedStatus(
  proposalKey: string
): PersistedMealProposalStatus | null {
  const rawValue = readStorageItem(statusStorageKey(proposalKey));
  if (!rawValue) {
    return null;
  }

  try {
    const parsedValue = JSON.parse(
      rawValue
    ) as Partial<PersistedMealProposalStatus>;
    if (
      parsedValue.version !== STATUS_VERSION ||
      !isMealProposalPhase(parsedValue.phase)
    ) {
      resetMealProposalStatus(proposalKey);
      return null;
    }

    return {
      version: STATUS_VERSION,
      phase: parsedValue.phase,
      updatedAt:
        typeof parsedValue.updatedAt === 'string'
          ? parsedValue.updatedAt
          : undefined,
      proposalInstanceId:
        typeof parsedValue.proposalInstanceId === 'string'
          ? parsedValue.proposalInstanceId
          : undefined,
      recipeId:
        typeof parsedValue.recipeId === 'string'
          ? parsedValue.recipeId
          : undefined,
      returnContext:
        parsedValue.returnContext &&
        typeof parsedValue.returnContext === 'object'
          ? parsedValue.returnContext
          : undefined,
      lastError:
        typeof parsedValue.lastError === 'string'
          ? parsedValue.lastError
          : undefined,
    };
  } catch {
    resetMealProposalStatus(proposalKey);
    return null;
  }
}

function readLegacyFlag(
  proposalKey: string,
  statusKey: LegacyMealProposalStatusKey
): boolean {
  return readStorageItem(legacyStorageKey(proposalKey, statusKey)) === '1';
}

function clearLegacyStatus(proposalKey: string): void {
  for (const legacyStatusKey of LEGACY_STATUS_KEYS) {
    removeStorageItem(legacyStorageKey(proposalKey, legacyStatusKey));
  }
}

function migrateLegacyStatus(
  proposalKey: string
): PersistedMealProposalStatus | null {
  const savedToBook = readLegacyFlag(proposalKey, 'savedToBook');
  const addedToPlan = readLegacyFlag(proposalKey, 'addedToPlan');
  const rejected = readLegacyFlag(proposalKey, 'rejected');

  if (!savedToBook && !addedToPlan && !rejected) {
    return null;
  }

  const phase: MealProposalPhase = rejected
    ? 'rejected'
    : addedToPlan
      ? 'added_to_plan'
      : savedToBook
        ? 'recipe_saved'
        : 'pending';

  const nextStatus: PersistedMealProposalStatus = {
    version: STATUS_VERSION,
    phase,
    updatedAt: new Date().toISOString(),
  };

  persistStatus(proposalKey, nextStatus);

  return nextStatus;
}

function persistStatus(
  proposalKey: string,
  status: PersistedMealProposalStatus
): void {
  writeStorageItem(statusStorageKey(proposalKey), JSON.stringify(status));
  clearLegacyStatus(proposalKey);
}

function toStatusView(
  persistedStatus: PersistedMealProposalStatus
): MealProposalStatus {
  const savedToBook =
    persistedStatus.phase === 'recipe_saved' ||
    persistedStatus.phase === 'adding_to_plan' ||
    persistedStatus.phase === 'retryable_add_failure';

  return {
    version: persistedStatus.version,
    phase: persistedStatus.phase,
    updatedAt: persistedStatus.updatedAt,
    proposalInstanceId: persistedStatus.proposalInstanceId,
    recipeId: persistedStatus.recipeId,
    returnContext: persistedStatus.returnContext,
    lastError: persistedStatus.lastError,
    savedToBook,
    addedToPlan: persistedStatus.phase === 'added_to_plan',
    rejected: persistedStatus.phase === 'rejected',
    canRetryAdd:
      persistedStatus.phase === 'recipe_saved' ||
      persistedStatus.phase === 'retryable_add_failure',
  };
}

function getStoredMealProposalStatus(
  proposalKey: string
): PersistedMealProposalStatus {
  return (
    readPersistedStatus(proposalKey) ??
    migrateLegacyStatus(proposalKey) ?? {
      version: STATUS_VERSION,
      phase: 'pending',
    }
  );
}

export function getMealProposalStatus(proposalKey: string): MealProposalStatus {
  return toStatusView(getStoredMealProposalStatus(proposalKey));
}

export function setMealProposalStatus(
  proposalKey: string,
  update: MealProposalStatusUpdate
): void {
  const currentStatus = getStoredMealProposalStatus(proposalKey);
  const nextStatus: PersistedMealProposalStatus = {
    ...currentStatus,
    ...update,
    version: STATUS_VERSION,
    updatedAt: new Date().toISOString(),
  };

  if (
    update.phase !== 'retryable_add_failure' &&
    update.lastError === undefined
  ) {
    delete nextStatus.lastError;
  }

  persistStatus(proposalKey, nextStatus);
}

export function markMealProposalSavedToBook(
  proposalKey: string,
  context?: Omit<MealProposalStatusUpdate, 'phase'>
): void {
  setMealProposalStatus(proposalKey, {
    ...context,
    phase: 'recipe_saved',
  });
}

export function markMealProposalAddedToPlan(
  proposalKey: string,
  context?: Omit<MealProposalStatusUpdate, 'phase'>
): void {
  setMealProposalStatus(proposalKey, {
    ...context,
    phase: 'added_to_plan',
  });
}

export function markMealProposalRetryableAddFailure(
  proposalKey: string,
  context?: Omit<MealProposalStatusUpdate, 'phase'>
): void {
  setMealProposalStatus(proposalKey, {
    ...context,
    phase: 'retryable_add_failure',
  });
}

export function markMealProposalRejected(
  proposalKey: string,
  context?: Omit<MealProposalStatusUpdate, 'phase'>
): void {
  setMealProposalStatus(proposalKey, {
    ...context,
    phase: 'rejected',
  });
}

export function resetMealProposalStatus(proposalKey: string): void {
  removeStorageItem(statusStorageKey(proposalKey));
  clearLegacyStatus(proposalKey);
}

export function invalidateMealProposalStatus(
  proposalKey: string,
  proposalInstanceId: string
): void {
  const currentStatus = readPersistedStatus(proposalKey);
  if (
    !currentStatus ||
    (currentStatus.proposalInstanceId &&
      currentStatus.proposalInstanceId === proposalInstanceId)
  ) {
    return;
  }

  resetMealProposalStatus(proposalKey);
}
