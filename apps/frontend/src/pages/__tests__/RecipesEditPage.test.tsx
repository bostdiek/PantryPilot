import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import RecipesEditPage from '../RecipesEditPage';
import type { Recipe } from '../../types/Recipe';

const mockNavigate = vi.fn();

const baseRecipe: Recipe = {
  id: 'r1',
  title: 'Spaghetti',
  description: 'Classic pasta',
  ingredients: [
    { name: 'Pasta', quantity_value: 200, quantity_unit: 'g' },
    { name: 'Tomato', prep: { method: 'chopped' } },
  ],
  instructions: ['Boil water', 'Cook pasta'],
  prep_time_minutes: 5,
  cook_time_minutes: 10,
  total_time_minutes: 15,
  serving_min: 2,
  serving_max: 4,
  difficulty: 'easy',
  category: 'dinner',
  ethnicity: 'Italian',
  oven_temperature_f: undefined,
  user_notes: '',
  link_source: '',
  ai_summary: '',
  created_at: new Date('2024-01-01'),
  updated_at: new Date('2024-01-01'),
};

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => ({ id: 'r1' }),
    useLoaderData: () => baseRecipe,
  };
});

const mockUpdateRecipe = vi.fn();

vi.mock('../../stores/useRecipeStore', () => ({
  useRecipeStore: () => ({ updateRecipe: mockUpdateRecipe }),
}));

// Mock Select to a simple native select to avoid Headless UI + SVG issues in jsdom
vi.mock('../../components/ui/Select', () => ({
  Select: ({ options, value, onChange, label }: any) => (
    <label>
      {label}
      <select
        aria-label={label}
        value={value?.id}
        onChange={(e) =>
          onChange(options.find((o: any) => o.id === e.target.value))
        }
      >
        {options.map((o: any) => (
          <option key={o.id} value={o.id}>
            {o.name}
          </option>
        ))}
      </select>
    </label>
  ),
}));

describe('RecipesEditPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('pre-populates form with recipe data and updates on submit', async () => {
    const user = userEvent.setup();
    render(<RecipesEditPage />);

    // Pre-populated name
    const nameInput = screen.getByLabelText(/recipe name/i) as HTMLInputElement;
    expect(nameInput.value).toBe('Spaghetti');

    // Update title
    await user.clear(nameInput);
    await user.type(nameInput, 'Spaghetti Bolognese');

    // Ensure ingredients are rendered and update first ingredient quantity
    const qtyInputs = screen.getAllByLabelText(/qty/i) as HTMLInputElement[];
    expect(qtyInputs[0].value).toBe('200');
    await user.clear(qtyInputs[0]);
    await user.type(qtyInputs[0], '250');

    // Submit
    const submit = screen.getByRole('button', { name: /update recipe/i });
    mockUpdateRecipe.mockResolvedValue({
      ...baseRecipe,
      title: 'Spaghetti Bolognese',
    });
    await user.click(submit);

    // Called with mapped payload
    expect(mockUpdateRecipe).toHaveBeenCalled();
    const [, payload] = mockUpdateRecipe.mock.calls[0];
    expect(payload.title).toBe('Spaghetti Bolognese');
    // Ingredients mapped: quantity_unit becomes undefined when empty
    const pasta = payload.ingredients.find((i: any) => i.name === 'Pasta');
    expect(pasta.quantity_value).toBe(250);

    // Navigates back to detail
    expect(mockNavigate).toHaveBeenCalledWith('/recipes/r1');
  });
});
