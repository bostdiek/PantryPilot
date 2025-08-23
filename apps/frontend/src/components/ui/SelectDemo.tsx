import { useState } from 'react';
import { Select } from './Select';

/**
 * SelectDemo component that demonstrates the usage of our Select component
 */
export function SelectDemo() {
  // Sample options for different selects
  const difficulties = [
    { id: 'easy', name: 'Easy' },
    { id: 'medium', name: 'Medium' },
    { id: 'hard', name: 'Hard' },
  ];

  const categories = [
    { id: 'breakfast', name: 'Breakfast' },
    { id: 'lunch', name: 'Lunch' },
    { id: 'dinner', name: 'Dinner' },
    { id: 'dessert', name: 'Dessert' },
    { id: 'snack', name: 'Snack' },
  ];

  const servings = [
    { id: '1', name: '1 Serving' },
    { id: '2', name: '2 Servings' },
    { id: '4', name: '4 Servings' },
    { id: '6', name: '6 Servings' },
    { id: '8', name: '8 Servings' },
  ];

  // State for the different selects
  const [selectedDifficulty, setSelectedDifficulty] = useState(difficulties[0]);
  const [selectedCategory, setSelectedCategory] = useState(categories[0]);
  const [selectedServing, setSelectedServing] = useState(servings[1]);

  return (
    <div className="space-y-8 p-6">
      {/* Basic Select */}
      <section>
        <h2 className="mb-4 text-lg font-semibold">Basic Select</h2>
        <div className="w-64">
          <Select
            options={difficulties}
            value={selectedDifficulty}
            onChange={setSelectedDifficulty}
            label="Difficulty"
          />
        </div>
      </section>

      {/* Select with Label */}
      <section>
        <h2 className="mb-4 text-lg font-semibold">Select with Labels</h2>
        <div className="grid grid-cols-2 gap-4">
          <Select
            options={categories}
            value={selectedCategory}
            onChange={setSelectedCategory}
            label="Category"
          />
          <Select
            options={servings}
            value={selectedServing}
            onChange={setSelectedServing}
            label="Servings"
          />
        </div>
      </section>

      {/* Disabled Select */}
      <section>
        <h2 className="mb-4 text-lg font-semibold">Disabled Select</h2>
        <div className="w-64">
          <Select
            options={difficulties}
            value={selectedDifficulty}
            onChange={setSelectedDifficulty}
            label="Difficulty (Disabled)"
            disabled
          />
        </div>
      </section>
    </div>
  );
}
