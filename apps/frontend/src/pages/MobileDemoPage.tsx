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
      <Card
        className={`p-3 select-none ${!isMobile ? 'cursor-grab' : ''}`}
      >
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <div className="mb-1 text-base font-medium">{mockRecipe.title}</div>
            <div className="mb-2 text-xs text-gray-600">
              {mockRecipe.total_time_minutes} min • {mockRecipe.difficulty}
            </div>
            <div className="mt-1 text-xs text-gray-500">
              {isMobile ? 'Tap "Add" to add to a day' : 'Drag to a day to add'}
            </div>
            {selectedDay && (
              <div className="mt-2 text-xs text-green-600 font-medium">
                ✓ Added to {selectedDay}
              </div>
            )}
          </div>
          
          {/* Mobile Add Button */}
          {isMobile && (
            <Button
              variant="primary"
              size="sm"
              onClick={handleMobileAdd}
              className="ml-2 shrink-0"
              aria-label={`Add ${mockRecipe.title} to meal plan`}
            >
              Add
            </Button>
          )}

          {/* Desktop Drag Handle Placeholder */}
          {!isMobile && (
            <div className="ml-2 shrink-0 text-gray-400 text-xs cursor-grab">
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
      <div className="py-6 space-y-6">
        <div className="text-center">
          <h1 className="text-2xl font-bold mb-2">Mobile Meal Planning Demo</h1>
          <p className="text-gray-600">
            Current viewport: <span className="font-semibold">{isMobile ? 'Mobile' : 'Desktop'}</span>
          </p>
          <p className="text-sm text-gray-500 mt-1">
            Resize your browser window to see the differences
          </p>
        </div>

        <div className="grid gap-4">
          <div>
            <h2 className="text-lg font-semibold mb-3">Recipe Card Behavior:</h2>
            <DemoRecipeCard />
          </div>

          <Card className="p-4 bg-blue-50 border-blue-200">
            <h3 className="font-semibold text-blue-900 mb-2">
              {isMobile ? '📱 Mobile Experience' : '🖥️ Desktop Experience'}
            </h3>
            <ul className="text-sm text-blue-800 space-y-1">
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
                  <li>• "Add" button hidden to save space</li>
                  <li>• Full drag-and-drop functionality</li>
                  <li>• Traditional desktop interaction</li>
                </>
              )}
            </ul>
          </Card>

          <div className="text-center">
            <p className="text-xs text-gray-500">
              This demo shows the responsive behavior of the recipe cards in the meal planning interface.
              The actual implementation includes full drag-and-drop functionality on desktop
              and touch-optimized interactions on mobile devices.
            </p>
          </div>
        </div>
      </div>
    </Container>
  );
}