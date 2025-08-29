import type { Ingredient } from '../types/Ingredients';

// Normalize raw ingredient inputs for form state (ensure optional fields are present)
export function normalizeIngredientsForForm(
  inputs: Ingredient[]
): Ingredient[] {
  if (!inputs || inputs.length === 0) {
    return [
      {
        name: '',
        quantity_value: undefined,
        quantity_unit: '',
        prep: {},
        is_optional: false,
      },
    ];
  }

  return inputs.map((ing) => ({
    name: ing.name || '',
    quantity_value: ing.quantity_value ?? undefined,
    quantity_unit: ing.quantity_unit ?? '',
    prep: ing.prep ?? {},
    is_optional: ing.is_optional ?? false,
  }));
}

// Prepare ingredients payload for API by stripping empty optional fields
export function mapIngredientsForApi(inputs: Ingredient[]) {
  return inputs
    .filter((ing) => ing.name.trim() !== '')
    .map((ing) => ({
      name: ing.name,
      quantity_value: ing.quantity_value,
      quantity_unit: ing.quantity_unit || undefined,
      prep:
        ing.prep && (ing.prep.method || ing.prep.size_descriptor)
          ? {
              method: ing.prep.method,
              size_descriptor: ing.prep.size_descriptor,
            }
          : undefined,
      is_optional: ing.is_optional ?? false,
    }));
}
