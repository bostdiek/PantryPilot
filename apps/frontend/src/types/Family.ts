type FamilyMember = {
  name: string;
  dietaryRestrictions: string[];
  allergies: string[];
  preferredCuisines: string[];
};

type Family = {
  members: FamilyMember[];
};

export type { Family, FamilyMember };
