export type IngredientPrep = {
  method?: string;
  size_descriptor?: string;
};

type Ingredient = {
  id?: string;
  name: string;
  quantity_value?: number;
  quantity_unit?: string;
  prep?: IngredientPrep;
  is_optional?: boolean;
};

export type { Ingredient };
