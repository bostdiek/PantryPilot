export type MealProposalStatus = {
  savedToBook: boolean;
  addedToPlan: boolean;
  rejected: boolean;
};

const KEY_PREFIX = 'pantrypilot_meal_proposal';

type MealProposalStatusKey = keyof MealProposalStatus;

function key(proposalKey: string, statusKey: MealProposalStatusKey): string {
  return `${KEY_PREFIX}:${proposalKey}:${statusKey}`;
}

function readFlag(
  proposalKey: string,
  statusKey: MealProposalStatusKey
): boolean {
  try {
    return localStorage.getItem(key(proposalKey, statusKey)) === '1';
  } catch {
    return false;
  }
}

function writeFlag(
  proposalKey: string,
  statusKey: MealProposalStatusKey,
  value: boolean
): void {
  try {
    if (value) {
      localStorage.setItem(key(proposalKey, statusKey), '1');
    } else {
      localStorage.removeItem(key(proposalKey, statusKey));
    }
  } catch {
    // localStorage might be unavailable (privacy mode, etc.)
  }
}

export function getMealProposalStatus(proposalKey: string): MealProposalStatus {
  return {
    savedToBook: readFlag(proposalKey, 'savedToBook'),
    addedToPlan: readFlag(proposalKey, 'addedToPlan'),
    rejected: readFlag(proposalKey, 'rejected'),
  };
}

export function markMealProposalSavedToBook(proposalKey: string): void {
  writeFlag(proposalKey, 'savedToBook', true);
}

export function markMealProposalAddedToPlan(proposalKey: string): void {
  writeFlag(proposalKey, 'addedToPlan', true);
}

export function markMealProposalRejected(proposalKey: string): void {
  writeFlag(proposalKey, 'rejected', true);
}
