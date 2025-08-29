import { describe, it, expect } from 'vitest';
import {
  mapIngredientsForApi,
  normalizeIngredientsForForm,
} from '../ingredients';

describe('ingredients utils', () => {
  it('normalizeIngredientsForForm returns default row when empty', () => {
    const result = normalizeIngredientsForForm([]);
    expect(result).toHaveLength(1);
    expect(result[0]).toMatchObject({ name: '', quantity_unit: '', prep: {} });
  });

  it('normalizeIngredientsForForm fills optional fields', () => {
    const result = normalizeIngredientsForForm([{ name: 'Onion' }]);
    expect(result[0]).toMatchObject({
      name: 'Onion',
      quantity_value: undefined,
      quantity_unit: '',
      prep: {},
      is_optional: false,
    });
  });

  it('mapIngredientsForApi filters empty names and strips empty optionals', () => {
    const result = mapIngredientsForApi([
      {
        name: 'Onion',
        quantity_value: 1,
        quantity_unit: '',
        prep: {},
        is_optional: false,
      },
      { name: '', quantity_value: 2 },
      { name: 'Garlic', prep: { method: '', size_descriptor: '' } },
      { name: 'Tomato', prep: { method: 'chopped' } },
    ]);

    // Garlic has empty prep and should be stripped to undefined prep, but it's still a valid ingredient
    expect(result).toHaveLength(3);
    expect(result[0]).toMatchObject({
      name: 'Onion',
      quantity_unit: undefined,
      prep: undefined,
    });
    expect(result[1]).toMatchObject({ name: 'Garlic', prep: undefined });
    expect(result[2]).toMatchObject({
      name: 'Tomato',
      prep: { method: 'chopped', size_descriptor: undefined },
    });
  });
});
