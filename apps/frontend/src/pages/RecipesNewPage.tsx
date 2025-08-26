import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Container } from '../components/ui/Container';
import { Input } from '../components/ui/Input';
import { Select } from '../components/ui/Select';

const RecipesNewPage: React.FC = () => {
  const navigate = useNavigate();
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  // Category options
  const categoryOptions = [
    { id: 'breakfast', name: 'Breakfast' },
    { id: 'lunch', name: 'Lunch' },
    { id: 'dinner', name: 'Dinner' },
  ];
  const [category, setCategory] = useState(categoryOptions[0]);
  const [prepTime, setPrepTime] = useState(0);
  const [cookTime, setCookTime] = useState(0);
  const [servings, setServings] = useState(1);
  const [ingredients, setIngredients] = useState(['']);
  const [instructions, setInstructions] = useState(['']);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // TODO: handle recipe creation
    navigate('/recipes');
  };

  return (
    <Container size="md">
      <Card variant="default" className="mt-6 p-6">
        <h1 className="mb-4 text-2xl font-bold">Create New Recipe</h1>
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Name & Description */}
          <Input
            label="Recipe Name"
            value={title}
            onChange={setTitle}
            placeholder="Enter recipe name"
            required
          />
          <Input
            label="Description"
            value={description}
            onChange={setDescription}
            placeholder="Brief description of the recipe"
          />

          {/* Category Select */}
          <Select
            label="Category"
            options={categoryOptions}
            value={category}
            onChange={setCategory}
          />

          {/* Prep, Cook, Servings */}
          <div className="grid grid-cols-3 gap-4">
            <Input
              label="Prep (min)"
              type="number"
              value={prepTime.toString()}
              onChange={(v) => setPrepTime(Number(v))}
            />
            <Input
              label="Cook (min)"
              type="number"
              value={cookTime.toString()}
              onChange={(v) => setCookTime(Number(v))}
            />
            <Input
              label="Servings"
              type="number"
              value={servings.toString()}
              onChange={(v) => setServings(Number(v))}
            />
          </div>

          {/* Ingredients List */}
          <div className="space-y-2">
            <h2 className="text-lg font-semibold">Ingredients</h2>
            {ingredients.map((ing, idx) => (
              <div key={idx} className="flex items-center space-x-2">
                <Input
                  className="flex-1"
                  value={ing}
                  onChange={(v) => {
                    const list = [...ingredients];
                    list[idx] = v;
                    setIngredients(list);
                  }}
                  placeholder={`Ingredient ${idx + 1}`}
                />
                {ingredients.length > 1 && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      const list = [...ingredients];
                      list.splice(idx, 1);
                      setIngredients(list);
                    }}
                  >
                    Remove
                  </Button>
                )}
              </div>
            ))}
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setIngredients([...ingredients, ''])}
            >
              + Add Ingredient
            </Button>
          </div>

          {/* Instructions List */}
          <div className="space-y-2">
            <h2 className="text-lg font-semibold">Instructions</h2>
            {instructions.map((step, idx) => (
              <div key={idx} className="flex items-center space-x-2">
                <Input
                  className="flex-1"
                  value={step}
                  onChange={(v) => {
                    const list = [...instructions];
                    list[idx] = v;
                    setInstructions(list);
                  }}
                  placeholder={`Step ${idx + 1}`}
                />
                {instructions.length > 1 && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      const list = [...instructions];
                      list.splice(idx, 1);
                      setInstructions(list);
                    }}
                  >
                    Remove
                  </Button>
                )}
              </div>
            ))}
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setInstructions([...instructions, ''])}
            >
              + Add Step
            </Button>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end space-x-2">
            <Button
              type="button"
              variant="ghost"
              onClick={() => navigate('/recipes')}
            >
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              Save Recipe
            </Button>
          </div>
        </form>
      </Card>
    </Container>
  );
};

export default RecipesNewPage;
