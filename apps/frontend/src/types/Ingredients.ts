export type IngredientPrep = {
  method?: string;
  size_descriptor?: string;
  size_count?: number;
  size_unit?: string;
  cut_style?: string;
  estimated_weight_g?: number;
  notes?: string;
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
