import { useState } from 'react';
import { Combobox } from './Combobox';

/**
 * ComboboxDemo component that demonstrates the usage of our Combobox component
 */
export function ComboboxDemo() {
  // Sample data for the different comboboxes
  const ingredients = [
    { id: 'tomato', name: 'Tomato' },
    { id: 'onion', name: 'Onion' },
    { id: 'garlic', name: 'Garlic' },
    { id: 'potato', name: 'Potato' },
    { id: 'carrot', name: 'Carrot' },
    { id: 'chicken', name: 'Chicken' },
    { id: 'beef', name: 'Beef' },
    { id: 'pasta', name: 'Pasta' },
    { id: 'rice', name: 'Rice' },
    { id: 'olive-oil', name: 'Olive Oil' },
  ];

  const kitchenTools = [
    { id: 'knife', name: "Chef's Knife" },
    { id: 'cutting-board', name: 'Cutting Board' },
    { id: 'pot', name: 'Cooking Pot' },
    { id: 'pan', name: 'Frying Pan' },
    { id: 'whisk', name: 'Whisk' },
    { id: 'spatula', name: 'Spatula' },
    { id: 'blender', name: 'Blender' },
    { id: 'measuring-cups', name: 'Measuring Cups' },
    { id: 'measuring-spoons', name: 'Measuring Spoons' },
    { id: 'mixing-bowl', name: 'Mixing Bowl' },
  ];

  // State for the different comboboxes
  const [selectedIngredient, setSelectedIngredient] = useState(ingredients[0]);
  const [selectedTool, setSelectedTool] = useState(kitchenTools[0]);

  return (
    <div className="space-y-8 p-6">
      {/* Basic Combobox */}
      <section>
        <h2 className="mb-4 text-lg font-semibold">Basic Combobox</h2>
        <div className="w-64">
          <Combobox
            options={ingredients}
            value={selectedIngredient}
            onChange={setSelectedIngredient}
            label="Search Ingredients"
          />
        </div>
      </section>

      {/* Combobox with Placeholder */}
      <section>
        <h2 className="mb-4 text-lg font-semibold">
          Combobox with Custom Placeholder
        </h2>
        <div className="w-64">
          <Combobox
            options={kitchenTools}
            value={selectedTool}
            onChange={setSelectedTool}
            label="Kitchen Tools"
            placeholder="Search for a tool..."
          />
        </div>
      </section>

      {/* Disabled Combobox */}
      <section>
        <h2 className="mb-4 text-lg font-semibold">Disabled Combobox</h2>
        <div className="w-64">
          <Combobox
            options={ingredients}
            value={selectedIngredient}
            onChange={setSelectedIngredient}
            label="Ingredients (Disabled)"
            disabled
          />
        </div>
      </section>

      {/* Multiple Comboboxes */}
      <section>
        <h2 className="mb-4 text-lg font-semibold">Multiple Comboboxes</h2>
        <div className="grid grid-cols-2 gap-4">
          <Combobox
            options={ingredients}
            value={selectedIngredient}
            onChange={setSelectedIngredient}
            label="Primary Ingredient"
          />
          <Combobox
            options={kitchenTools}
            value={selectedTool}
            onChange={setSelectedTool}
            label="Required Tool"
          />
        </div>
      </section>
    </div>
  );
}
