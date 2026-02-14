import type { FC } from 'react';
import { useMemo, useState } from 'react';
import type { MealEntry, WeeklyMealPlan } from '../types/MealPlan';
import type { Recipe } from '../types/Recipe';
import { AddMealDialog } from './AddMealDialog';
import { MobileMealCard } from './MobileMealCard';
import { Badge } from './ui/Badge';
import { Button } from './ui/Button';
import { Card } from './ui/Card';
import { Disclosure } from './ui/Disclosure';
import ChevronDownIcon from './ui/icons/chevron-down.svg?react';
import ChevronLeftIcon from './ui/icons/chevron-left.svg?react';
import ChevronRightIcon from './ui/icons/chevron-right.svg?react';

export interface MobileMealPlanViewProps {
  /**
   * The current week's meal plan data
   */
  currentWeek: WeeklyMealPlan | null;

  /**
   * All available recipes for lookup
   */
  recipes: Recipe[];

  /**
   * Today's date in YYYY-MM-DD format
   */
  todayDate: string;

  /**
   * The start date of the current week (YYYY-MM-DD format)
   */
  currentWeekStart?: string;

  /**
   * Callback when week navigation is triggered
   */
  onWeekChange?: (direction: 'prev' | 'next' | 'today') => void;

  /**
   * Callback when a recipe should be added to an entry
   */
  onAddRecipeToEntry?: (entryId: string) => void;

  /**
   * Callback when an entry should be marked as cooked
   */
  onMarkCooked?: (entryId: string) => void;

  /**
   * Callback when a recipe is clicked (for preview)
   */
  onRecipeClick?: (entryId: string, date: string) => void;

  /**
   * Callback when an entry should be removed
   */
  onRemoveEntry?: (entryId: string) => void;

  /**
   * Callback when a leftover should be added to a date
   */
  onAddLeftover?: (date: string) => void;

  /**
   * Callback when an eating out entry should be added to a date
   */
  onAddEatingOut?: (date: string) => void;
}

interface DayData {
  date: string;
  dayOfWeek: string;
  entries: MealEntry[];
  isToday: boolean;
}

/**
 * Mobile-optimized meal plan view with focused daily layout
 *
 * Features:
 * - Today's meals prominently displayed
 * - Next few days in collapsible sections
 * - Touch-friendly interactions
 * - No horizontal scrolling
 */
export const MobileMealPlanView: FC<MobileMealPlanViewProps> = ({
  currentWeek,
  recipes,
  todayDate,
  currentWeekStart,
  onWeekChange,
  onAddRecipeToEntry,
  onMarkCooked,
  onRecipeClick,
  onRemoveEntry,
  onAddLeftover,
  onAddEatingOut,
}) => {
  // AddMealDialog state
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [addDialogTarget, setAddDialogTarget] = useState<{
    date: string;
    dayOfWeek: string;
  } | null>(null);

  const handleOpenAddDialog = (date: string, dayOfWeek: string) => {
    setAddDialogTarget({ date, dayOfWeek });
    setAddDialogOpen(true);
  };

  const handleCloseAddDialog = () => {
    setAddDialogOpen(false);
    setAddDialogTarget(null);
  };

  // Organize days into past, today, and upcoming
  const { pastDays, todayData, upcomingDays } = useMemo(() => {
    if (!currentWeek) {
      return { pastDays: [], todayData: null, upcomingDays: [] };
    }

    const today = currentWeek.days.find((day) => day.date === todayDate);
    const past = currentWeek.days.filter((day) => day.date < todayDate);
    const upcoming = currentWeek.days.filter((day) => day.date > todayDate);

    return {
      pastDays: past.map((day) => ({
        date: day.date,
        dayOfWeek: day.dayOfWeek,
        entries: day.entries,
        isToday: false,
      })),
      todayData: today
        ? {
            date: today.date,
            dayOfWeek: today.dayOfWeek,
            entries: today.entries,
            isToday: true,
          }
        : null,
      upcomingDays: upcoming.map((day) => ({
        date: day.date,
        dayOfWeek: day.dayOfWeek,
        entries: day.entries,
        isToday: false,
      })),
    };
  }, [currentWeek, todayDate]);

  // Helper to find recipe for an entry
  const getRecipeForEntry = (entry: MealEntry): Recipe | null => {
    if (!entry.recipeId) return null;
    return recipes.find((r) => r.id === entry.recipeId) || null;
  };

  // Check if the displayed week contains today
  const isCurrentWeek = useMemo(() => {
    if (!currentWeekStart) return true;
    const weekStart = new Date(currentWeekStart + 'T00:00:00');
    const todayD = new Date(todayDate + 'T00:00:00');
    const weekEnd = new Date(weekStart);
    weekEnd.setDate(weekEnd.getDate() + 6);
    return todayD >= weekStart && todayD <= weekEnd;
  }, [currentWeekStart, todayDate]);

  // Helper to format week start date for header
  const formatWeekStart = (dateStr: string): string => {
    const date = new Date(dateStr + 'T00:00:00');
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    });
  };

  // Helper to format date for display
  const formatDate = (dateStr: string): string => {
    const date = new Date(dateStr + 'T00:00:00');
    return date.toLocaleDateString('en-US', {
      weekday: 'long',
      month: 'long',
      day: 'numeric',
    });
  };

  // Helper to format short date
  const formatShortDate = (dateStr: string): string => {
    const date = new Date(dateStr + 'T00:00:00');
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    });
  };

  const renderDayMeals = (dayData: DayData) => {
    return (
      <div className="space-y-3">
        {dayData.entries.length === 0 ? (
          <div className="rounded-lg bg-gray-50 p-4 text-center text-sm text-gray-500">
            No meals planned for this day
          </div>
        ) : (
          dayData.entries.map((entry) => (
            <MobileMealCard
              key={entry.id}
              entry={entry}
              recipe={getRecipeForEntry(entry)}
              onAddRecipe={() => onAddRecipeToEntry?.(entry.id)}
              onMarkCooked={() => onMarkCooked?.(entry.id)}
              onRecipeClick={() => onRecipeClick?.(entry.id, dayData.date)}
              onRemove={() => onRemoveEntry?.(entry.id)}
            />
          ))
        )}
      </div>
    );
  };

  if (!currentWeek) {
    return (
      <div className="py-8 text-center text-gray-500">Loading meal plan...</div>
    );
  }

  return (
    <div className="space-y-4 md:hidden">
      {/* Week Navigation Header */}
      {onWeekChange && currentWeekStart && (
        <div className="sticky top-0 z-10 flex items-center justify-between border-b bg-white p-4">
          <button
            onClick={() => onWeekChange('prev')}
            className="flex min-h-[44px] min-w-[44px] items-center justify-center rounded-lg p-2 text-gray-600 hover:bg-gray-100 hover:text-gray-900"
            aria-label="Previous week"
          >
            <ChevronLeftIcon className="h-5 w-5" />
          </button>

          <div className="text-center">
            <span className="text-sm font-medium">
              Week of {formatWeekStart(currentWeekStart)}
            </span>
            {!isCurrentWeek && (
              <button
                onClick={() => onWeekChange('today')}
                className="block w-full text-xs text-blue-600 hover:underline"
              >
                📍 Jump to Today
              </button>
            )}
          </div>

          <button
            onClick={() => onWeekChange('next')}
            className="flex min-h-[44px] min-w-[44px] items-center justify-center rounded-lg p-2 text-gray-600 hover:bg-gray-100 hover:text-gray-900"
            aria-label="Next week"
          >
            <ChevronRightIcon className="h-5 w-5" />
          </button>
        </div>
      )}

      {/* Past days - collapsible */}
      {pastDays.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-lg font-semibold text-gray-900">
            Earlier This Week
          </h3>
          {pastDays.map((day) => (
            <Disclosure
              key={day.date}
              defaultOpen={false}
              title={
                <div className="flex w-full items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="font-medium">{day.dayOfWeek}</span>
                    <span className="text-sm text-gray-600">
                      {formatShortDate(day.date)}
                    </span>
                    <Badge variant="secondary">
                      {day.entries.length}{' '}
                      {day.entries.length === 1 ? 'meal' : 'meals'}
                    </Badge>
                  </div>
                </div>
              }
              className="rounded-md border border-gray-200 bg-white"
              buttonClassName="w-full justify-between p-4 hover:bg-gray-50 bg-white"
              panelClassName="px-4 pb-4"
              iconSvg={ChevronDownIcon}
            >
              <div className="mt-2 space-y-2">
                {renderDayMeals(day)}
                <Button
                  variant="outline"
                  size="sm"
                  fullWidth
                  onClick={() => handleOpenAddDialog(day.date, day.dayOfWeek)}
                  className="mt-3 min-h-[44px]"
                  aria-label={`Add meal to ${day.dayOfWeek}`}
                >
                  + Add to {day.dayOfWeek}
                </Button>
              </div>
            </Disclosure>
          ))}
        </div>
      )}

      {/* Today's meals - prominently featured */}
      {todayData && (
        <Card className="border-primary-200 from-primary-50 to-primary-100 bg-gradient-to-r">
          <div className="p-4">
            <div className="mb-2 flex items-center justify-between">
              <h2 className="text-primary-900 text-xl font-bold">Today</h2>
              <Button
                variant="primary"
                size="sm"
                onClick={() =>
                  handleOpenAddDialog(todayData.date, todayData.dayOfWeek)
                }
                className="min-h-[44px] min-w-[44px]"
                aria-label={`Add meal to ${todayData.dayOfWeek}`}
              >
                + Add
              </Button>
            </div>
            <p className="text-primary-700 mb-4 text-sm">
              {formatDate(todayData.date)}
            </p>
            {renderDayMeals(todayData)}
          </div>
        </Card>
      )}

      {/* Next few days - collapsible */}
      {upcomingDays.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-lg font-semibold text-gray-900">Next Few Days</h3>
          {upcomingDays.map((day) => (
            <Disclosure
              key={day.date}
              defaultOpen={false}
              title={
                <div className="flex w-full items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="font-medium">{day.dayOfWeek}</span>
                    <span className="text-sm text-gray-600">
                      {formatShortDate(day.date)}
                    </span>
                    <Badge variant="secondary">
                      {day.entries.length}{' '}
                      {day.entries.length === 1 ? 'meal' : 'meals'}
                    </Badge>
                  </div>
                </div>
              }
              className="rounded-md border border-gray-200 bg-white"
              buttonClassName="w-full justify-between p-4 hover:bg-gray-50 bg-white"
              panelClassName="px-4 pb-4"
              iconSvg={ChevronDownIcon}
            >
              <div className="mt-2 space-y-2">
                {renderDayMeals(day)}
                <Button
                  variant="outline"
                  size="sm"
                  fullWidth
                  onClick={() => handleOpenAddDialog(day.date, day.dayOfWeek)}
                  className="mt-3 min-h-[44px]"
                  aria-label={`Add meal to ${day.dayOfWeek}`}
                >
                  + Add to {day.dayOfWeek}
                </Button>
              </div>
            </Disclosure>
          ))}
        </div>
      )}

      {/* AddMealDialog */}
      <AddMealDialog
        isOpen={addDialogOpen}
        onClose={handleCloseAddDialog}
        targetDate={addDialogTarget?.date ?? ''}
        dayOfWeek={addDialogTarget?.dayOfWeek ?? ''}
        onAddLeftover={() => {
          if (addDialogTarget && onAddLeftover) {
            onAddLeftover(addDialogTarget.date);
          }
        }}
        onAddEatingOut={() => {
          if (addDialogTarget && onAddEatingOut) {
            onAddEatingOut(addDialogTarget.date);
          }
        }}
      />
    </div>
  );
};
