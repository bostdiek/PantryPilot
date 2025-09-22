import React, { useState } from 'react';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Container } from '../components/ui/Container';
import { DaySelectionDialog } from '../components/recipes/DaySelectionDialog';
import { useIsMobile } from '../hooks/useMediaQuery';
import type { DayOption } from '../types/DayOption';

// Mock recipe data
const mockRecipe = {
  id: 'demo-recipe',
  title: 'Spaghetti Carbonara',
  description: 'Classic Italian pasta dish',
  ingredients: [],
  instructions: ['Cook pasta', 'Make sauce', 'Combine'],
  total_time_minutes: 30,
  difficulty: 'medium' as const,
  tags: ['italian', 'pasta'],
  created_at: '2025-01-01',
  updated_at: '2025-01-01',
};

// Mock week data
const mockDays: DayOption[] = [
  { dayOfWeek: 'Monday', date: '2025-01-13', isToday: false },
  { dayOfWeek: 'Tuesday', date: '2025-01-14', isToday: true },
  { dayOfWeek: 'Wednesday', date: '2025-01-15', isToday: false },
  { dayOfWeek: 'Thursday', date: '2025-01-16', isToday: false },
  { dayOfWeek: 'Friday', date: '2025-01-17', isToday: false },
  { dayOfWeek: 'Saturday', date: '2025-01-18', isToday: false },
  { dayOfWeek: 'Sunday', date: '2025-01-19', isToday: false },
];

function DemoRecipeCard() {
  const isMobile = useIsMobile();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedDay, setSelectedDay] = useState<string | null>(null);

  const handleMobileAdd = () => {
    setDialogOpen(true);
  };

  const handleDaySelect = (dayOfWeek: string, date: string) => {
    setSelectedDay(`${dayOfWeek} (${date})`);
    setDialogOpen(false);
    // In real app, this would call the meal plan store
    alert(`Added "${mockRecipe.title}" to ${dayOfWeek}!`);
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
  };

  return (
    <>
      <Card className={`p-3 select-none ${!isMobile ? 'cursor-grab' : ''}`}>
        <div className="flex items-start justify-between">
          <div className="min-w-0 flex-1">
            <div className="mb-1 text-base font-medium">{mockRecipe.title}</div>
            <div className="mb-2 text-xs text-gray-600">
              {mockRecipe.total_time_minutes} min • {mockRecipe.difficulty}
            </div>
            <div className="mt-1 text-xs text-gray-500">
              {isMobile
                ? 'Tap "Add" to add to a day'
                : 'Drag to a day to add or use "Add" button'}
            </div>
            {selectedDay && (
              <div className="mt-2 text-xs font-medium text-green-600">
                ✓ Added to {selectedDay}
              </div>
            )}
          </div>

          {/* Add Button - available on both mobile and desktop */}
          <Button
            variant="primary"
            size="sm"
            onClick={handleMobileAdd}
            className="ml-2 shrink-0"
            aria-label={`Add ${mockRecipe.title} to meal plan`}
          >
            Add
          </Button>

          {/* Desktop Drag Handle Indicator - shown alongside Add button */}
          {!isMobile && (
            <div className="ml-2 shrink-0 cursor-grab text-xs text-gray-400">
              ⋮⋮ Drag
            </div>
          )}
        </div>
      </Card>

      <DaySelectionDialog
        isOpen={dialogOpen}
        onClose={handleCloseDialog}
        onDaySelect={handleDaySelect}
        recipeTitle={mockRecipe.title}
        availableDays={mockDays}
      />
    </>
  );
}

/**
 * Demo page showcasing mobile vs desktop recipe card behavior
 */
export default function MobileDemoPage() {
  const isMobile = useIsMobile();

  return (
    <Container>
      <div className="space-y-6 py-6">
        <div className="text-center">
          <h1 className="mb-2 text-2xl font-bold">Mobile Meal Planning Demo</h1>
          <p className="text-gray-600">
            Current viewport:{' '}
            <span className="font-semibold">
              {isMobile ? 'Mobile' : 'Desktop'}
            </span>
          </p>
          <p className="mt-1 text-sm text-gray-500">
            Resize your browser window to see the differences
          </p>
        </div>

        <div className="grid gap-4">
          <div>
            <h2 className="mb-3 text-lg font-semibold">
              Recipe Card Behavior:
            </h2>
            <DemoRecipeCard />
          </div>

          <Card className="border-blue-200 bg-blue-50 p-4">
            <h3 className="mb-2 font-semibold text-blue-900">
              {isMobile ? '📱 Mobile Experience' : '🖥️ Desktop Experience'}
            </h3>
            <ul className="space-y-1 text-sm text-blue-800">
              {isMobile ? (
                <>
                  <li>• "Add" button visible for easy tapping</li>
                  <li>• No drag functionality to prevent scroll conflicts</li>
                  <li>• Day selection dialog opens on tap</li>
                  <li>• Touch-friendly interface</li>
                </>
              ) : (
                <>
                  <li>• Drag handle visible for mouse interaction</li>
                  <li>• "Add" button also available for convenience</li>
                  <li>• Full drag-and-drop functionality</li>
                  <li>• Dual interaction options (drag or click Add)</li>
                </>
              )}
            </ul>
          </Card>

          <div className="text-center">
            <p className="text-xs text-gray-500">
              This demo shows the responsive behavior of the recipe cards in the
              meal planning interface. The implementation provides "Add" buttons
              on all devices for easy access, plus full drag-and-drop
              functionality on desktop for users who prefer that interaction
              method.
            </p>
          </div>
        </div>
      </div>
    </Container>
  );
}
