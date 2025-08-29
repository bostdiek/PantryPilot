import { useState } from 'react';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Select, type SelectOption } from '../ui/Select';
import { Icon } from '../ui/Icon';
import SearchIcon from '../ui/icons/search.svg?react';
import XIcon from '../ui/icons/x.svg?react';
import { RECIPE_CATEGORIES, RECIPE_DIFFICULTIES, type RecipeCategory, type RecipeDifficulty } from '../../types/Recipe';
import { useRecipeFilters } from '../../hooks/useRecipeFilters';
import type { RecipeSortOption } from '../../stores/useRecipeStore';

interface RecipeSearchFiltersProps {
  className?: string;
}

// Sort options for the dropdown
const sortOptions: { value: RecipeSortOption; label: string }[] = [
  { value: 'relevance', label: 'Best Match' },
  { value: 'title-asc', label: 'Title A-Z' },
  { value: 'title-desc', label: 'Title Z-A' },
  { value: 'cook-time-asc', label: 'Cook Time (Low to High)' },
  { value: 'cook-time-desc', label: 'Cook Time (High to Low)' },
  { value: 'recently-added', label: 'Recently Added' },
];

// Convert sort options to Select format
const sortSelectOptions: SelectOption[] = sortOptions.map(option => ({
  id: option.value,
  name: option.label,
}));

// Convert categories to filter button format
const categoryOptions = RECIPE_CATEGORIES.map(cat => ({
  id: cat,
  name: cat.charAt(0).toUpperCase() + cat.slice(1),
}));

// Convert difficulties to filter button format
const difficultyOptions = RECIPE_DIFFICULTIES.map(diff => ({
  id: diff,
  name: diff.charAt(0).toUpperCase() + diff.slice(1),
}));

/**
 * Recipe search and filter component
 * Provides search input, category/difficulty filters, cook time range, and sort options
 */
export function RecipeSearchFilters({ className = '' }: RecipeSearchFiltersProps) {
  const { filters, sortBy, setFilters, setSortBy, clearFilters } = useRecipeFilters();
  
  // Local state for ingredient inputs
  const [includeInput, setIncludeInput] = useState('');
  const [excludeInput, setExcludeInput] = useState('');
  
  // Expanded state for advanced filters
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Handle search input changes
  const handleSearchChange = (query: string) => {
    setFilters({ query });
  };

  // Handle category selection (multi-select)
  const handleCategoryChange = (option: { id: string; name: string }) => {
    const category = option.id as RecipeCategory;
    const newCategories = filters.categories.includes(category)
      ? filters.categories.filter(c => c !== category)
      : [...filters.categories, category];
    setFilters({ categories: newCategories });
  };

  // Handle difficulty selection (multi-select)
  const handleDifficultyChange = (option: { id: string; name: string }) => {
    const difficulty = option.id as RecipeDifficulty;
    const newDifficulties = filters.difficulties.includes(difficulty)
      ? filters.difficulties.filter(d => d !== difficulty)
      : [...filters.difficulties, difficulty];
    setFilters({ difficulties: newDifficulties });
  };

  // Handle cook time range changes
  const handleCookTimeMinChange = (value: string) => {
    const min = parseInt(value, 10);
    if (!isNaN(min)) {
      setFilters({ cookTimeMin: min });
    }
  };

  const handleCookTimeMaxChange = (value: string) => {
    const max = parseInt(value, 10);
    if (!isNaN(max)) {
      setFilters({ cookTimeMax: max });
    }
  };

  // Handle ingredient filters
  const addIncludedIngredient = () => {
    if (includeInput.trim()) {
      setFilters({ 
        includedIngredients: [...filters.includedIngredients, includeInput.trim()] 
      });
      setIncludeInput('');
    }
  };

  const removeIncludedIngredient = (ingredient: string) => {
    setFilters({ 
      includedIngredients: filters.includedIngredients.filter(i => i !== ingredient)
    });
  };

  const addExcludedIngredient = () => {
    if (excludeInput.trim()) {
      setFilters({ 
        excludedIngredients: [...filters.excludedIngredients, excludeInput.trim()] 
      });
      setExcludeInput('');
    }
  };

  const removeExcludedIngredient = (ingredient: string) => {
    setFilters({ 
      excludedIngredients: filters.excludedIngredients.filter(i => i !== ingredient)
    });
  };

  // Handle sort change
  const handleSortChange = (option: SelectOption) => {
    setSortBy(option.id as RecipeSortOption);
  };

  // Check if any filters are active
  const hasActiveFilters = 
    filters.query ||
    filters.categories.length > 0 ||
    filters.difficulties.length > 0 ||
    filters.cookTimeMin > 0 ||
    filters.cookTimeMax < 240 ||
    filters.includedIngredients.length > 0 ||
    filters.excludedIngredients.length > 0 ||
    sortBy !== 'relevance';

  return (
    <div className={`space-y-4 rounded-lg border border-gray-200 bg-white p-4 shadow-sm ${className}`}>
      {/* Search and Sort Row */}
      <div className="flex flex-col gap-4 sm:flex-row">
        <div className="flex-1">
          <Input
            value={filters.query}
            onChange={handleSearchChange}
            type="search"
            placeholder="Search recipes and ingredients..."
            leftIconSvg={SearchIcon}
            className="w-full"
            label="Search"
          />
        </div>
        <div className="sm:w-64">
          <Select
            options={sortSelectOptions}
            value={sortSelectOptions.find(opt => opt.id === sortBy) || sortSelectOptions[0]}
            onChange={handleSortChange}
            label="Sort by"
          />
        </div>
      </div>

      {/* Basic Filters Row */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Category</label>
          <div className="flex flex-wrap gap-2">
            {categoryOptions.map(option => (
              <button
                key={option.id}
                onClick={() => handleCategoryChange(option)}
                className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                  filters.categories.includes(option.id as RecipeCategory)
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {option.name}
              </button>
            ))}
          </div>
        </div>
        
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Difficulty</label>
          <div className="flex flex-wrap gap-2">
            {difficultyOptions.map(option => (
              <button
                key={option.id}
                onClick={() => handleDifficultyChange(option)}
                className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                  filters.difficulties.includes(option.id as RecipeDifficulty)
                    ? 'bg-green-500 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {option.name}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Advanced Filters Toggle */}
      <div className="flex items-center justify-between">
        <Button
          variant="ghost"
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="text-sm"
        >
          {showAdvanced ? 'Hide' : 'Show'} Advanced Filters
        </Button>
        
        {hasActiveFilters && (
          <Button
            variant="outline"
            onClick={clearFilters}
            className="text-sm"
          >
            Clear All Filters
          </Button>
        )}
      </div>

      {/* Advanced Filters */}
      {showAdvanced && (
        <div className="space-y-4 border-t border-gray-200 pt-4">
          {/* Cook Time Range */}
          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700">
              Total Cook Time (minutes)
            </label>
            <div className="grid grid-cols-2 gap-4">
              <Input
                value={filters.cookTimeMin.toString()}
                onChange={handleCookTimeMinChange}
                type="number"
                placeholder="Min"
                label="Minimum"
              />
              <Input
                value={filters.cookTimeMax.toString()}
                onChange={handleCookTimeMaxChange}
                type="number"
                placeholder="Max"
                label="Maximum"
              />
            </div>
          </div>

          {/* Include Ingredients */}
          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700">
              Must Include Ingredients
            </label>
            <div className="flex gap-2">
              <Input
                value={includeInput}
                onChange={setIncludeInput}
                placeholder="Add ingredient..."
                className="flex-1"
              />
              <Button
                variant="outline"
                onClick={addIncludedIngredient}
                disabled={!includeInput.trim()}
              >
                Add
              </Button>
            </div>
            {filters.includedIngredients.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-2">
                {filters.includedIngredients.map(ingredient => (
                  <span
                    key={ingredient}
                    className="flex items-center gap-1 rounded-full bg-green-100 px-2 py-1 text-xs"
                  >
                    {ingredient}
                    <button
                      onClick={() => removeIncludedIngredient(ingredient)}
                      className="text-green-600 hover:text-green-800"
                    >
                      <Icon svg={XIcon} className="h-3 w-3" />
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Exclude Ingredients */}
          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700">
              Must Exclude Ingredients
            </label>
            <div className="flex gap-2">
              <Input
                value={excludeInput}
                onChange={setExcludeInput}
                placeholder="Add ingredient to exclude..."
                className="flex-1"
              />
              <Button
                variant="outline"
                onClick={addExcludedIngredient}
                disabled={!excludeInput.trim()}
              >
                Add
              </Button>
            </div>
            {filters.excludedIngredients.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-2">
                {filters.excludedIngredients.map(ingredient => (
                  <span
                    key={ingredient}
                    className="flex items-center gap-1 rounded-full bg-red-100 px-2 py-1 text-xs"
                  >
                    {ingredient}
                    <button
                      onClick={() => removeExcludedIngredient(ingredient)}
                      className="text-red-600 hover:text-red-800"
                    >
                      <Icon svg={XIcon} className="h-3 w-3" />
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}