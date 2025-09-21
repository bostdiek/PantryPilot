import type {
  DragEndEvent,
  DragOverEvent,
  DragStartEvent,
} from '@dnd-kit/core';
import {
  DndContext,
  DragOverlay,
  KeyboardSensor,
  PointerSensor,
  useDraggable,
  useDroppable,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { Menu, Transition } from '@headlessui/react';
import {
  Fragment,
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type FC,
  type ReactNode,
} from 'react';
import { searchRecipes } from '../api/endpoints/recipes';
import { RecipeQuickPreview } from '../components/RecipeQuickPreview';
import { DaySelectionDialog } from '../components/recipes/DaySelectionDialog';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Container } from '../components/ui/Container';
import { Icon } from '../components/ui/Icon';
import CheckIcon from '../components/ui/icons/check.svg?react';
import DragHandleIcon from '../components/ui/icons/drag-handle.svg?react';
import XIcon from '../components/ui/icons/x.svg?react';
import { Input } from '../components/ui/Input';
import { Select, type SelectOption } from '../components/ui/Select';
import { useIsMobile } from '../hooks/useMediaQuery';
import { useMealPlanStore } from '../stores/useMealPlanStore';
import { useRecipeStore } from '../stores/useRecipeStore';
import type { DayOption } from '../types/DayOption';
import type { Recipe, RecipeCategory, RecipeDifficulty } from '../types/Recipe';

function toYyyyMmDd(d: Date): string {
  return d.toISOString().slice(0, 10);
}

const MealPlanPage: FC = () => {
  const {
    currentWeek,
    isLoading,
    error,
    addEntry,
    updateEntry,
    removeEntry,
    loadWeek,
  } = useMealPlanStore();
  const today = useMemo(() => new Date(), []);
  const isMobile = useIsMobile();

  // Week helpers
  function startOfSundayWeek(d: Date): Date {
    const day = new Date(d);
    const dow = day.getUTCDay();
    const start = new Date(
      Date.UTC(day.getUTCFullYear(), day.getUTCMonth(), day.getUTCDate())
    );
    start.setUTCDate(start.getUTCDate() - dow);
    return start;
  }
  function fmtYmd(d: Date): string {
    return d.toISOString().slice(0, 10);
  }
  function addDays(ymd: string, days: number): string {
    const [y, m, d] = ymd.split('-').map((n) => Number(n));
    const dt = new Date(Date.UTC(y, m - 1, d));
    dt.setUTCDate(dt.getUTCDate() + days);
    return fmtYmd(dt);
  }

  // Load week on mount
  useEffect(() => {
    if (!currentWeek) {
      const start = fmtYmd(startOfSundayWeek(today));
      void loadWeek(start);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Horizontal scroll helpers to reveal the full day card in view
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const dayRefs = useRef<Map<string, HTMLDivElement>>(new Map());
  const lastScrolledWeekStart = useRef<string | null>(null);
  function registerDayRef(date: string, el: HTMLDivElement | null) {
    const map = dayRefs.current;
    if (!el) {
      map.delete(date);
    } else {
      map.set(date, el);
      // Auto-scroll to today once per loaded week when today's card mounts
      const todayStr = toYyyyMmDd(today);
      if (
        currentWeek &&
        date === todayStr &&
        lastScrolledWeekStart.current !== currentWeek.weekStartDate
      ) {
        requestAnimationFrame(() => scrollToDay(todayStr, 'auto'));
        lastScrolledWeekStart.current = currentWeek.weekStartDate;
      }
    }
  }
  function scrollToDay(date: string, behavior: ScrollBehavior = 'smooth') {
    const container = scrollRef.current;
    const el = dayRefs.current.get(date);
    if (!container || !el) return;
    const margin = 16; // px padding so the card isn't flush to the edge
    const elLeft = el.offsetLeft;
    const elRight = elLeft + el.offsetWidth;
    const viewLeft = container.scrollLeft;
    const viewRight = viewLeft + container.clientWidth;

    let targetLeft = viewLeft;
    if (elLeft - margin < viewLeft) {
      // Scroll left so the whole card is visible
      targetLeft = elLeft - margin;
    } else if (elRight + margin > viewRight) {
      // Scroll right just enough to reveal the card fully
      targetLeft = elRight - container.clientWidth + margin;
    }
    targetLeft = Math.max(0, targetLeft);
    container.scrollTo({ left: targetLeft, behavior });
  }

  // Auto-scroll now occurs in registerDayRef when today's card mounts

  // Recipes (labels and search)
  const { recipes } = useRecipeStore();
  const [query, setQuery] = useState('');
  const [difficulty, setDifficulty] = useState<SelectOption | null>(null);
  const [category, setCategory] = useState<SelectOption | null>(null);
  const [maxTime, setMaxTime] = useState('');
  const [pageLimit, setPageLimit] = useState(12);
  const [pageOffset, setPageOffset] = useState(0);
  const [pageItems, setPageItems] = useState<Recipe[]>([]);
  const [pageTotal, setPageTotal] = useState<number | null | undefined>(
    undefined
  );
  const [pageLoading, setPageLoading] = useState(false);
  const [pageError, setPageError] = useState<string | null>(null);
  const [showSearch, setShowSearch] = useState(true);

  // Recipe quick preview state
  const [previewRecipe, setPreviewRecipe] = useState<Recipe | null>(null);
  const [previewDateContext, setPreviewDateContext] = useState<string | null>(
    null
  );
  const [previewEntryId, setPreviewEntryId] = useState<string | null>(null);

  // Day selection dialog state (for mobile)
  const [daySelectionOpen, setDaySelectionOpen] = useState(false);
  const [selectedRecipeForDay, setSelectedRecipeForDay] = useState<Recipe | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { 
      activationConstraint: { distance: 6 },
      // Disable pointer sensor on mobile to prevent conflicts with scrolling
      disabled: isMobile,
    }),
    useSensor(KeyboardSensor, { 
      coordinateGetter: sortableKeyboardCoordinates,
      // Keep keyboard sensor enabled for accessibility
    })
  );

  const difficultyOptions: SelectOption[] = [
    { id: '', name: 'Any' },
    { id: 'easy', name: 'Easy' },
    { id: 'medium', name: 'Medium' },
    { id: 'hard', name: 'Hard' },
  ];
  const categoryOptions: SelectOption[] = [
    { id: '', name: 'Any' },
    { id: 'breakfast', name: 'Breakfast' },
    { id: 'lunch', name: 'Lunch' },
    { id: 'dinner', name: 'Dinner' },
    { id: 'dessert', name: 'Dessert' },
    { id: 'snack', name: 'Snack' },
    { id: 'appetizer', name: 'Appetizer' },
  ];

  // Server-side recipe search
  useEffect(() => {
    let cancelled = false;
    const t = setTimeout(async () => {
      setPageLoading(true);
      setPageError(null);
      try {
        const resp = await searchRecipes({
          query: query.trim() || undefined,
          difficulty: (difficulty?.id as RecipeDifficulty) || undefined,
          category: (category?.id as RecipeCategory) || undefined,
          max_total_time: maxTime ? Number(maxTime) : undefined,
          limit: pageLimit,
          offset: pageOffset,
        });
        if (cancelled) return;
        setPageItems(resp.items);
        setPageTotal(resp.total);
      } catch (e) {
        if (cancelled) return;
        setPageError(e instanceof Error ? e.message : 'Failed to load recipes');
        setPageItems([]);
        setPageTotal(undefined);
      } finally {
        if (!cancelled) setPageLoading(false);
      }
    }, 200);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [query, difficulty, category, maxTime, pageLimit, pageOffset]);

  function getEntryLabelById(entryId: string): string {
    const entry = currentWeek?.days
      .flatMap((d) => d.entries)
      .find((e) => e.id === entryId);
    if (!entry) return 'Planned item';
    if (entry.isEatingOut) return 'Eating out';
    if (entry.isLeftover) return 'Leftovers';
    if (entry.recipeId) {
      const recipe = recipes.find((r) => r.id === entry.recipeId);
      return recipe ? recipe.title : `Recipe • ${entry.recipeId.slice(0, 8)}…`;
    }
    return 'Planned item';
  }

  function getNextOrderIndex(date: string): number {
    const day = currentWeek?.days.find((d) => d.date === date);
    if (!day || day.entries.length === 0) return 0;
    return Math.max(...day.entries.map((e) => e.orderIndex)) + 1;
  }

  // Recipe preview handlers
  function handleRecipeClick(entryId: string, date: string) {
    const entry = currentWeek?.days
      .flatMap((d) => d.entries)
      .find((e) => e.id === entryId);

    if (!entry?.recipeId) return;

    const recipe = recipes.find((r) => r.id === entry.recipeId);
    if (recipe) {
      setPreviewRecipe(recipe);
      setPreviewDateContext(date);
      setPreviewEntryId(entryId);
    }
  }

  function handleClosePreview() {
    setPreviewRecipe(null);
    setPreviewDateContext(null);
    setPreviewEntryId(null);
  }

  async function handleRemoveFromDay() {
    if (previewEntryId) {
      try {
        await removeEntry(previewEntryId);
        // Close the modal after successful removal
        handleClosePreview();
      } catch (error) {
        console.error('Failed to remove entry:', error);
        // Don't close modal on error so user can try again
      }
    }
  }

  // Mobile day selection functions
  function handleMobileAddRecipe(recipe: Recipe) {
    setSelectedRecipeForDay(recipe);
    setDaySelectionOpen(true);
  }

  async function handleDaySelect(dayOfWeek: string, date: string) {
    if (!selectedRecipeForDay) return;
    
    const nextIndex = getNextOrderIndex(date);
    try {
      await addEntry({
        plannedForDate: date,
        recipeId: selectedRecipeForDay.id,
        orderIndex: nextIndex,
      });
    } catch (error) {
      console.error('Failed to add recipe to day:', error);
    }
  }

  function handleCloseDaySelection() {
    setDaySelectionOpen(false);
    setSelectedRecipeForDay(null);
  }

  async function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    setActiveDrag(null);
    setOverDayDate(null);
    setOverEntryId(null);
    if (!over) return;
    const activeType = active.data.current?.type as string | undefined;
    const overType = over.data.current?.type as string | undefined;
    const overId = over.id as string | undefined;

    if (activeType === 'recipe') {
      let dayDate: string | null = null;
      if (overType === 'day') {
        dayDate = (over.data.current?.date as string) ?? null;
      } else if (overId?.startsWith('entry-') && currentWeek) {
        const targetEntryId = overId.replace('entry-', '');
        const targetDay = currentWeek.days.find((d) =>
          d.entries.some((e) => e.id === targetEntryId)
        );
        dayDate = targetDay?.date ?? null;
      }
      if (!dayDate) return;
      const nextIndex = getNextOrderIndex(dayDate);
      const recipeId = active.data.current?.recipeId as string;
      await addEntry({
        plannedForDate: dayDate,
        recipeId,
        orderIndex: nextIndex,
      });
      return;
    }

    if (activeType === 'entry' && currentWeek) {
      const entryId = active.data.current?.entryId as string;
      const sourceDay = currentWeek.days.find((d) =>
        d.entries.some((e) => e.id === entryId)
      );
      if (!sourceDay) return;
      const sourceIds = sourceDay.entries.map((e) => e.id);
      const fromIndex = sourceIds.indexOf(entryId);
      if (fromIndex === -1) return;

      let targetDay = sourceDay;
      let toIndex = sourceIds.length - 1;

      if (overType === 'day') {
        const overDayDate = over.data.current?.date as string;
        targetDay =
          currentWeek.days.find((d) => d.date === overDayDate) ?? sourceDay;
        toIndex = targetDay.entries.length;
      } else if (overId?.startsWith('entry-')) {
        const overEntryId = overId.replace('entry-', '');
        const dayContainingOver = currentWeek.days.find((d) =>
          d.entries.some((e) => e.id === overEntryId)
        );
        if (dayContainingOver) {
          targetDay = dayContainingOver;
          const targetIds = targetDay.entries.map((e) => e.id);
          toIndex = targetIds.indexOf(overEntryId);
          if (toIndex === -1) toIndex = targetIds.length;
        }
      }

      if (targetDay.date === sourceDay.date && fromIndex === toIndex) return;

      const newSourceIds =
        sourceDay.date === targetDay.date
          ? arrayMove(sourceIds, fromIndex, toIndex)
          : sourceIds.filter((id) => id !== entryId);

      const targetIdsPre = targetDay.entries.map((e) => e.id);
      const newTargetIds =
        sourceDay.date === targetDay.date
          ? newSourceIds
          : [
              ...targetIdsPre.slice(0, toIndex),
              entryId,
              ...targetIdsPre.slice(toIndex),
            ];

      const updates: Promise<void>[] = [];
      for (let i = 0; i < newTargetIds.length; i++) {
        const id = newTargetIds[i];
        const existing = targetDay.entries.find((e) => e.id === id);
        const needsMove = id === entryId && targetDay.date !== sourceDay.date;
        const indexChanged = existing ? existing.orderIndex !== i : true;
        if (needsMove || indexChanged) {
          updates.push(
            updateEntry(id, { plannedForDate: targetDay.date, orderIndex: i })
          );
        }
      }

      if (sourceDay.date !== targetDay.date) {
        for (let i = 0; i < newSourceIds.length; i++) {
          const id = newSourceIds[i];
          const existing = sourceDay.entries.find((e) => e.id === id);
          if (!existing || existing.orderIndex !== i) {
            updates.push(
              updateEntry(id, { orderIndex: i, plannedForDate: sourceDay.date })
            );
          }
        }
      }

      if (updates.length) {
        await Promise.all(updates);
      }
    }
  }

  function handleDragStart(event: DragStartEvent) {
    const { active } = event;
    const activeType = active.data.current?.type as string | undefined;
    if (activeType === 'recipe') {
      setActiveDrag({
        type: 'recipe',
        recipeId: active.data.current?.recipeId,
      });
    } else if (activeType === 'entry') {
      setActiveDrag({ type: 'entry', entryId: active.data.current?.entryId });
    }
  }

  function handleDragCancel() {
    setActiveDrag(null);
    setOverDayDate(null);
    setOverEntryId(null);
  }

  const [activeDrag, setActiveDrag] = useState<
    | { type: 'recipe'; recipeId: string }
    | { type: 'entry'; entryId: string }
    | null
  >(null);
  const [overDayDate, setOverDayDate] = useState<string | null>(null);
  const [overEntryId, setOverEntryId] = useState<string | null>(null);

  function handleDragOver(event: DragOverEvent) {
    const { over } = event;
    if (!over) {
      setOverDayDate(null);
      setOverEntryId(null);
      return;
    }
    const overType = over.data.current?.type as string | undefined;
    if (overType === 'day') {
      setOverDayDate((over.data.current?.date as string) ?? null);
      setOverEntryId(null);
    } else if (
      typeof over.id === 'string' &&
      over.id.startsWith('entry-') &&
      currentWeek
    ) {
      const targetEntryId = (over.id as string).replace('entry-', '');
      const targetDay = currentWeek.days.find((d) =>
        d.entries.some((e) => e.id === targetEntryId)
      );
      setOverDayDate(targetDay?.date ?? null);
      setOverEntryId(targetEntryId);
    } else {
      setOverDayDate(null);
      setOverEntryId(null);
    }
  }

  function DayDroppableCard({
    date,
    isToday,
    title,
    children,
  }: {
    date: string;
    isToday: boolean;
    title: string;
    children: ReactNode;
  }) {
    const { setNodeRef, isOver } = useDroppable({
      id: `day-${date}`,
      data: { type: 'day', date },
    });
    return (
      <Card
        ref={setNodeRef}
        variant={isToday ? 'elevated' : 'default'}
        className={[
          'min-h-[320px] sm:min-h-[360px]',
          isToday ? 'border-primary-500 border-2' : '',
          isOver ? 'ring-primary-400 ring-2' : '',
        ].join(' ')}
      >
        <div className="p-4">
          <div className="mb-2 flex items-baseline justify-between">
            <div className="font-semibold">{title}</div>
            <div className="text-xs text-gray-500">{date}</div>
          </div>
          {children}
        </div>
      </Card>
    );
  }

  function DraggableRecipeCard({ recipe }: { recipe: Recipe }) {
    const { attributes, listeners, setNodeRef } = useDraggable({
      id: `recipe-${recipe.id}`,
      data: { type: 'recipe', recipeId: recipe.id },
      disabled: isMobile, // Disable dragging on mobile
    });
    
    return (
      <Card
        ref={setNodeRef}
        className={`p-3 select-none ${!isMobile ? 'cursor-grab' : ''}`}
        {...(!isMobile ? listeners : {})}
        {...(!isMobile ? attributes : {})}
      >
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <div className="mb-1 text-base font-medium">{recipe.title}</div>
            <div className="mb-2 text-xs text-gray-600">
              {recipe.total_time_minutes} min • {recipe.difficulty}
            </div>
            <div className="mt-1 text-xs text-gray-500">
              {isMobile ? 'Tap "Add" to add to a day' : 'Drag to a day to add'}
            </div>
          </div>
          
          {/* Mobile Add Button - visible only on mobile */}
          {isMobile && (
            <Button
              variant="primary"
              size="sm"
              onClick={() => handleMobileAddRecipe(recipe)}
              className="ml-2 shrink-0"
              aria-label={`Add ${recipe.title} to meal plan`}
            >
              Add
            </Button>
          )}
        </div>
      </Card>
    );
  }

  function DraggableEntryItem({
    entryId,
    label,
    meta,
    wasCooked,
    cookedAt,
    onCook,
    onRemove,
    isRecipe = false,
    onRecipeClick,
  }: {
    entryId: string;
    label: string;
    meta?: string;
    wasCooked: boolean;
    cookedAt?: string;
    onCook?: () => void;
    onRemove?: () => void;
    isRecipe?: boolean;
    onRecipeClick?: () => void;
  }) {
    const {
      attributes,
      listeners,
      setNodeRef,
      transform,
      transition,
      isDragging,
    } = useSortable({
      id: `entry-${entryId}`,
      data: { type: 'entry', entryId },
    });
    const style: CSSProperties = {
      transform: transform
        ? `translate3d(${transform.x}px, ${transform.y}px, 0)`
        : undefined,
      transition,
      opacity: isDragging ? 0.6 : 1,
    };
    return (
      <li
        ref={setNodeRef}
        className="flex min-h-[44px] items-start justify-between gap-3 rounded-md border border-gray-200 bg-white p-3 text-sm shadow-sm hover:shadow"
        style={style}
      >
        <span className="flex min-w-0 items-start gap-2">
          <button
            className="cursor-grab rounded px-1 py-0.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
            aria-label={`Drag ${label}`}
            {...listeners}
            {...attributes}
          >
            <Icon
              svg={DragHandleIcon}
              className="pointer-events-none h-5 w-5"
              title="Drag handle"
            />
          </button>
          <span className="min-w-0 flex-1">
            {isRecipe ? (
              <button
                onClick={onRecipeClick}
                className="w-full rounded-sm text-left focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 focus:outline-none"
                aria-label={`View ${label} recipe preview`}
              >
                <span className="block leading-5 font-medium break-words whitespace-normal text-blue-600 hover:text-blue-800">
                  {label}
                </span>
                {meta && (
                  <span className="mt-0.5 block text-xs text-gray-500">
                    {meta}
                  </span>
                )}
              </button>
            ) : (
              <span>
                <span className="block leading-5 font-medium break-words whitespace-normal">
                  {label}
                </span>
                {meta && (
                  <span className="mt-0.5 block text-xs text-gray-500">
                    {meta}
                  </span>
                )}
              </span>
            )}
          </span>
        </span>
        <span className="flex shrink-0 items-center gap-2">
          {wasCooked ? (
            <span
              className="rounded bg-green-100 px-2 py-0.5 text-xs text-green-700"
              title={
                cookedAt
                  ? `Cooked at ${new Date(cookedAt).toLocaleString()}`
                  : 'Cooked'
              }
            >
              cooked
            </span>
          ) : (
            <Button
              size="sm"
              variant="ghost"
              onClick={() => onCook?.()}
              className="shrink-0"
              aria-label={`Mark ${label} as cooked`}
              title="Mark cooked"
              leftIconSvg={CheckIcon}
            >
              <span className="sr-only">Cooked</span>
            </Button>
          )}
          <Button
            size="sm"
            variant="ghost"
            onClick={() => onRemove?.()}
            className="shrink-0 text-red-600 hover:bg-red-50"
            aria-label={`Remove ${label}`}
            title="Remove"
            leftIconSvg={XIcon}
          >
            <span className="sr-only">Remove</span>
          </Button>
        </span>
      </li>
    );
  }

  return (
    <Container>
      <div className="py-6">
        <h1 className="mb-4 text-2xl font-bold">Weekly Meal Plan</h1>
        {error && (
          <div className="mb-4 rounded-md border border-red-300 bg-red-50 p-3 text-red-700">
            {error}
          </div>
        )}

        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          <div className="text-sm text-gray-700">
            {currentWeek ? (
              <>
                Week of{' '}
                <span className="font-semibold">
                  {currentWeek.weekStartDate}
                </span>
                {' — '}
                <span className="font-semibold">
                  {addDays(currentWeek.weekStartDate, 6)}
                </span>
              </>
            ) : (
              <>Week loading…</>
            )}
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                const start =
                  currentWeek?.weekStartDate ??
                  fmtYmd(startOfSundayWeek(today));
                void loadWeek(addDays(start, -7));
              }}
              aria-label="Previous week"
            >
              Prev Week
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                const start =
                  currentWeek?.weekStartDate ??
                  fmtYmd(startOfSundayWeek(today));
                void loadWeek(addDays(start, 7));
              }}
              aria-label="Next week"
            >
              Next Week
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={async () => {
                const todayStart = fmtYmd(startOfSundayWeek(today));
                if (currentWeek?.weekStartDate !== todayStart) {
                  await loadWeek(todayStart);
                }
                // center after (re)render
                setTimeout(() => scrollToDay(toYyyyMmDd(today)), 0);
              }}
              aria-label="Jump to today"
            >
              Today
            </Button>
          </div>
        </div>

        <DndContext
          sensors={sensors}
          onDragStart={handleDragStart}
          onDragOver={handleDragOver}
          onDragEnd={handleDragEnd}
          onDragCancel={handleDragCancel}
        >
          {isLoading && <div className="mb-4">Loading weekly plan…</div>}
          {currentWeek && (
            <div className="overflow-x-auto" ref={scrollRef}>
              <div className="flex gap-4 pb-2">
                {currentWeek.days.map((day) => {
                  const isToday = day.date === toYyyyMmDd(today);
                  return (
                    <div
                      key={day.date}
                      className="min-w-[280px] shrink-0 md:min-w-[320px]"
                      ref={(el) => registerDayRef(day.date, el)}
                    >
                      <DayDroppableCard
                        date={day.date}
                        isToday={isToday}
                        title={day.dayOfWeek}
                      >
                        <SortableContext
                          items={day.entries.map((e) => `entry-${e.id}`)}
                          strategy={verticalListSortingStrategy}
                        >
                          <ul className="mb-3 space-y-3">
                            {day.entries.map((e) => (
                              <Fragment key={e.id}>
                                {overDayDate === day.date &&
                                  overEntryId === e.id && (
                                    <li className="border-primary-300 bg-primary-50/60 -my-1 h-2 rounded border-2 border-dashed" />
                                  )}
                                <DraggableEntryItem
                                  entryId={e.id}
                                  label={getEntryLabelById(e.id)}
                                  meta={(() => {
                                    if (e.recipeId) {
                                      const r = recipes.find(
                                        (r) => r.id === e.recipeId
                                      );
                                      if (r)
                                        return `${r.total_time_minutes} min • ${r.difficulty}`;
                                    }
                                    if (e.isLeftover) return 'Leftovers';
                                    if (e.isEatingOut) return 'Eating out';
                                    return undefined;
                                  })()}
                                  wasCooked={e.wasCooked}
                                  cookedAt={e.cookedAt}
                                  // Call markCooked from fresh store state so tests can spy/override after initial render
                                  onCook={() =>
                                    useMealPlanStore.getState().markCooked(e.id)
                                  }
                                  onRemove={() => removeEntry(e.id)}
                                  isRecipe={!!e.recipeId}
                                  onRecipeClick={() =>
                                    handleRecipeClick(e.id, day.date)
                                  }
                                />
                              </Fragment>
                            ))}
                            {day.entries.length === 0 && (
                              <li className="text-sm text-gray-400">
                                No entries
                              </li>
                            )}
                            {overDayDate === day.date &&
                              overEntryId === null && (
                                <li className="border-primary-300 bg-primary-50/40 text-primary-700 rounded border-2 border-dashed p-2 text-xs">
                                  Drop here
                                </li>
                              )}
                          </ul>
                        </SortableContext>
                        <div className="flex justify-end">
                          <Menu
                            as="div"
                            className="relative inline-block text-left"
                          >
                            <Menu.Button
                              as={Button}
                              variant="outline"
                              size="sm"
                              aria-label={`Add to ${day.dayOfWeek}`}
                            >
                              + Add
                            </Menu.Button>
                            <Transition
                              enter="transition ease-out duration-100"
                              enterFrom="transform opacity-0 scale-95"
                              enterTo="transform opacity-100 scale-100"
                              leave="transition ease-in duration-75"
                              leaveFrom="transform opacity-100 scale-100"
                              leaveTo="transform opacity-0 scale-95"
                            >
                              <Menu.Items className="absolute right-0 z-10 mt-2 w-36 origin-top-right rounded-md border border-gray-200 bg-white shadow-lg focus:outline-none">
                                <div className="py-1 text-sm">
                                  <Menu.Item as={Fragment}>
                                    {({ active }) => (
                                      <button
                                        className={[
                                          'block w-full px-3 py-1 text-left',
                                          active ? 'bg-gray-100' : '',
                                        ].join(' ')}
                                        onClick={() =>
                                          addEntry({
                                            plannedForDate: day.date,
                                            isLeftover: true,
                                          })
                                        }
                                      >
                                        Leftover
                                      </button>
                                    )}
                                  </Menu.Item>
                                  <Menu.Item as={Fragment}>
                                    {({ active }) => (
                                      <button
                                        className={[
                                          'block w-full px-3 py-1 text-left',
                                          active ? 'bg-gray-100' : '',
                                        ].join(' ')}
                                        onClick={() =>
                                          addEntry({
                                            plannedForDate: day.date,
                                            isEatingOut: true,
                                          })
                                        }
                                      >
                                        Eating Out
                                      </button>
                                    )}
                                  </Menu.Item>
                                </div>
                              </Menu.Items>
                            </Transition>
                          </Menu>
                        </div>
                      </DayDroppableCard>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Quick Search Recipes to Add */}
          <div className="mt-8">
            <div className="mb-2 flex items-center justify-between">
              <h2 className="text-xl font-semibold">Search Recipes to Add</h2>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowSearch((s) => !s)}
              >
                {showSearch ? 'Hide' : 'Show'} Search
              </Button>
            </div>
            {showSearch && (
              <Card className="p-4">
                <div className="grid grid-cols-1 gap-3 md:grid-cols-5">
                  <Input
                    label="Search"
                    value={query}
                    onChange={setQuery}
                    placeholder="Search recipes..."
                    className="md:col-span-2"
                  />
                  <Select
                    label="Difficulty"
                    options={difficultyOptions}
                    value={difficulty || difficultyOptions[0]}
                    onChange={(v) => setDifficulty(v.id ? v : null)}
                  />
                  <Input
                    label="Max Total Time (min)"
                    type="number"
                    value={maxTime}
                    onChange={setMaxTime}
                  />
                  <Select
                    label="Category"
                    options={categoryOptions}
                    value={category || categoryOptions[0]}
                    onChange={(v) => setCategory(v.id ? v : null)}
                  />
                </div>
              </Card>
            )}

            {showSearch && (
              <div className="mt-4">
                {pageError && (
                  <div className="mb-2 rounded border border-red-200 bg-red-50 p-2 text-sm text-red-700">
                    {pageError}
                  </div>
                )}
                <div className="mb-2 flex items-center justify-between text-xs text-gray-600">
                  <div>
                    {pageLoading
                      ? 'Loading recipes…'
                      : pageTotal != null
                        ? `Showing ${pageItems.length} of ${pageTotal} (offset ${pageOffset})`
                        : `Showing ${pageItems.length}`}
                  </div>
                  <div className="flex items-center gap-2">
                    <span>Per page:</span>
                    <select
                      className="rounded border border-gray-300 p-1"
                      value={pageLimit}
                      onChange={(e) => {
                        setPageLimit(Number(e.target.value));
                        setPageOffset(0);
                      }}
                    >
                      {[6, 12, 20, 50].map((n) => (
                        <option key={n} value={n}>
                          {n}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
                  {pageItems.map((r) => (
                    <DraggableRecipeCard key={r.id} recipe={r} />
                  ))}
                </div>
                <div className="mt-3 flex items-center justify-between">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={pageLoading || pageOffset === 0}
                    onClick={() =>
                      setPageOffset((o) => Math.max(0, o - pageLimit))
                    }
                  >
                    Prev
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={
                      pageLoading ||
                      (pageTotal != null
                        ? pageOffset + pageLimit >= pageTotal
                        : pageItems.length < pageLimit)
                    }
                    onClick={() => setPageOffset((o) => o + pageLimit)}
                  >
                    Next
                  </Button>
                </div>
              </div>
            )}
          </div>

          <DragOverlay>
            {activeDrag?.type === 'recipe' &&
              (() => {
                const recipe = recipes.find(
                  (r) =>
                    r.id ===
                    (activeDrag as { type: 'recipe'; recipeId: string })
                      .recipeId
                );
                return recipe ? (
                  <div className="w-60 cursor-grabbing rounded-md border bg-white p-3 shadow-lg select-none">
                    <div className="mb-1 text-base font-medium">
                      {recipe.title}
                    </div>
                    <div className="text-xs text-gray-600">
                      {recipe.total_time_minutes} min • {recipe.difficulty}
                    </div>
                  </div>
                ) : null;
              })()}
            {activeDrag?.type === 'entry' && (
              <div className="w-56 cursor-grabbing rounded bg-gray-50 p-2 text-sm shadow select-none">
                {getEntryLabelById(
                  (activeDrag as { type: 'entry'; entryId: string }).entryId
                )}
              </div>
            )}
          </DragOverlay>
        </DndContext>
      </div>

      {/* Recipe Quick Preview Modal */}
      <RecipeQuickPreview
        isOpen={!!previewRecipe}
        onClose={handleClosePreview}
        recipe={previewRecipe}
        dateContext={previewDateContext || undefined}
        onRemoveFromDay={handleRemoveFromDay}
      />

      {/* Day Selection Dialog for Mobile */}
      <DaySelectionDialog
        isOpen={daySelectionOpen}
        onClose={handleCloseDaySelection}
        onDaySelect={handleDaySelect}
        recipeTitle={selectedRecipeForDay?.title || ''}
        availableDays={
          currentWeek?.days.map((day): DayOption => ({
            dayOfWeek: day.dayOfWeek,
            date: day.date,
            isToday: day.date === toYyyyMmDd(today),
          })) || []
        }
      />
    </Container>
  );
};

export default MealPlanPage;
