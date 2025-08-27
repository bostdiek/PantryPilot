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
import React, { useEffect, useMemo, useState } from 'react';
import { searchRecipes } from '../api/endpoints/recipes';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Container } from '../components/ui/Container';
import { Input } from '../components/ui/Input';
import { Select, type SelectOption } from '../components/ui/Select';
import { useMealPlanStore } from '../stores/useMealPlanStore';
import { useRecipeStore } from '../stores/useRecipeStore';
import type { Recipe, RecipeCategory, RecipeDifficulty } from '../types/Recipe';

function toYyyyMmDd(d: Date): string {
  return d.toISOString().slice(0, 10);
}

// Helper retained if needed for week logic (currently unused)

const MealPlanPage: React.FC = () => {
  const { currentWeek, isLoading, error, addEntry, updateEntry, markCooked } =
    useMealPlanStore();
  const today = useMemo(() => new Date(), []);

  // Load recipes for labels/overlays; planner search below uses server-side pagination
  const { recipes } = useRecipeStore();

  // Quick search (client-side filter)
  const [query, setQuery] = useState('');
  const [difficulty, setDifficulty] = useState<SelectOption | null>(null);
  const [category, setCategory] = useState<SelectOption | null>(null);
  const [maxTime, setMaxTime] = useState('');
  // Server-side paginated search state
  const [pageLimit, setPageLimit] = useState(12);
  const [pageOffset, setPageOffset] = useState(0);
  const [pageItems, setPageItems] = useState<Recipe[]>([]);
  const [pageTotal, setPageTotal] = useState<number | null | undefined>(
    undefined
  );
  const [pageLoading, setPageLoading] = useState(false);
  const [pageError, setPageError] = useState<string | null>(null);
  // Track currently dragged item for DragOverlay
  const [activeDrag, setActiveDrag] = useState<
    | { type: 'recipe'; recipeId: string }
    | { type: 'entry'; entryId: string }
    | null
  >(null);
  // Track which day is currently hovered to show a drop placeholder
  const [overDayDate, setOverDayDate] = useState<string | null>(null);
  // Track which entry is hovered to show a between-item indicator
  const [overEntryId, setOverEntryId] = useState<string | null>(null);
  // DnD sensors (pointer + keyboard)
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
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

  // No day selector on recipe cards; users drag recipes directly into a day

  // Fetch paginated recipes for planner search (debounced)
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

  // Helper for entry label in lists and overlays
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

  // Helpers for DnD
  function getNextOrderIndex(date: string): number {
    const day = currentWeek?.days.find((d) => d.date === date);
    if (!day || day.entries.length === 0) return 0;
    return Math.max(...day.entries.map((e) => e.orderIndex)) + 1;
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

    // Dropping a recipe: add to the end of the target day
    if (activeType === 'recipe') {
      // Allow drop either on a day container or over another entry (interpreted as that entry's day)
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

    // Reordering/moving an existing entry using sortable semantics
    if (activeType === 'entry' && currentWeek) {
      const entryId = active.data.current?.entryId as string;

      // Find source day and index
      const sourceDay = currentWeek.days.find((d) =>
        d.entries.some((e) => e.id === entryId)
      );
      if (!sourceDay) return;
      const sourceIds = sourceDay.entries.map((e) => e.id);
      const fromIndex = sourceIds.indexOf(entryId);
      if (fromIndex === -1) return;

      // Determine target day and target index
      let targetDay = sourceDay;
      let toIndex = sourceIds.length - 1; // default to end of list

      if (overType === 'day') {
        const overDayDate = over.data.current?.date as string;
        targetDay =
          currentWeek.days.find((d) => d.date === overDayDate) ?? sourceDay;
        toIndex = targetDay.entries.length; // append
      } else if (overId?.startsWith('entry-')) {
        const overEntryId = overId.replace('entry-', '');
        const dayContainingOver = currentWeek.days.find((d) =>
          d.entries.some((e) => e.id === overEntryId)
        );
        if (dayContainingOver) {
          targetDay = dayContainingOver;
          const targetIds = targetDay.entries.map((e) => e.id);
          toIndex = targetIds.indexOf(overEntryId);
          if (toIndex === -1) toIndex = targetIds.length; // safety
        }
      }

      // If nothing changes, exit early
      if (targetDay.date === sourceDay.date && fromIndex === toIndex) return;

      // Build new ordered id arrays for source and target days
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

      // Persist updates (batch for efficiency)
      const updates: Promise<void>[] = [];
      // 1) Update target day entries
      for (let i = 0; i < newTargetIds.length; i++) {
        const id = newTargetIds[i];
        const existing = targetDay.entries.find((e) => e.id === id);
        const needsMove = id === entryId && targetDay.date !== sourceDay.date;
        const indexChanged = existing ? existing.orderIndex !== i : true;
        if (needsMove || indexChanged) {
          updates.push(
            updateEntry(id, {
              plannedForDate: targetDay.date,
              orderIndex: i,
            })
          );
        }
      }

      // 2) Update source day entries if moved across days
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

  // DnD subcomponents
  function DayDroppableCard({
    date,
    isToday,
    title,
    children,
  }: {
    date: string;
    isToday: boolean;
    title: string;
    children: React.ReactNode;
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
          isToday ? 'border-primary-500 border-2' : '',
          isOver ? 'ring-primary-400 ring-2' : '',
        ].join(' ')}
      >
        <div className="p-3">
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
    });
    return (
      <Card
        ref={setNodeRef}
        className="cursor-grab p-3 select-none"
        {...listeners}
        {...attributes}
      >
        <div className="mb-1 text-base font-medium">{recipe.title}</div>
        <div className="mb-2 text-xs text-gray-600">
          {recipe.total_time_minutes} min • {recipe.difficulty}
        </div>
        <div className="mt-1 text-xs text-gray-500">Drag to a day to add</div>
      </Card>
    );
  }

  function DraggableEntryItem({
    entryId,
    label,
    wasCooked,
    cookedAt,
    onCook,
  }: {
    entryId: string;
    label: string;
    wasCooked: boolean;
    cookedAt?: string;
    onCook?: () => void;
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
    const style: React.CSSProperties = {
      transform: transform
        ? `translate3d(${transform.x}px, ${transform.y}px, 0)`
        : undefined,
      transition,
      opacity: isDragging ? 0.6 : 1,
      cursor: 'grab',
    };
    return (
      <li
        ref={setNodeRef}
        className="flex items-center justify-between gap-2 rounded bg-gray-50 p-2 text-sm"
        style={style}
        {...listeners}
        {...attributes}
      >
        <span className="truncate">{label}</span>
        <span className="flex items-center gap-2">
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
              variant="outline"
              onClick={() => {
                onCook?.();
              }}
              className="shrink-0"
            >
              Cooked
            </Button>
          )}
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
        <DndContext
          sensors={sensors}
          onDragStart={handleDragStart}
          onDragOver={handleDragOver}
          onDragEnd={handleDragEnd}
          onDragCancel={handleDragCancel}
        >
          {isLoading && <div className="mb-4">Loading weekly plan…</div>}
          {currentWeek && (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7">
              {currentWeek.days.map((day) => {
                const isToday = day.date === toYyyyMmDd(today);
                return (
                  <DayDroppableCard
                    key={day.date}
                    date={day.date}
                    isToday={isToday}
                    title={day.dayOfWeek}
                  >
                    <SortableContext
                      items={day.entries.map((e) => `entry-${e.id}`)}
                      strategy={verticalListSortingStrategy}
                    >
                      <ul className="mb-3 space-y-2">
                        {day.entries.map((e) => (
                          <React.Fragment key={e.id}>
                            {overDayDate === day.date &&
                              overEntryId === e.id && (
                                <li className="border-primary-300 bg-primary-50/60 -my-1 h-2 rounded border-2 border-dashed" />
                              )}
                            <DraggableEntryItem
                              entryId={e.id}
                              label={getEntryLabelById(e.id)}
                              wasCooked={e.wasCooked}
                              cookedAt={e.cookedAt}
                              onCook={() => markCooked(e.id)}
                            />
                          </React.Fragment>
                        ))}
                        {day.entries.length === 0 && (
                          <li className="text-sm text-gray-500">No entries</li>
                        )}
                        {overDayDate === day.date && overEntryId === null && (
                          <li className="border-primary-300 bg-primary-50/40 text-primary-700 rounded border-2 border-dashed p-2 text-xs">
                            Drop here
                          </li>
                        )}
                      </ul>
                    </SortableContext>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() =>
                          addEntry({
                            plannedForDate: day.date,
                            isLeftover: true,
                          })
                        }
                      >
                        Add Leftover
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() =>
                          addEntry({
                            plannedForDate: day.date,
                            isEatingOut: true,
                          })
                        }
                      >
                        Eating Out
                      </Button>
                    </div>
                  </DayDroppableCard>
                );
              })}
            </div>
          )}

          {/* Quick Search Recipes to Add */}
          <div className="mt-8">
            <h2 className="mb-3 text-xl font-semibold">
              Search Recipes to Add
            </h2>
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
              {/* No search button needed for quick filter */}
            </Card>

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
          </div>
          {/* End Quick Search */}
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
    </Container>
  );
};

export default MealPlanPage;
