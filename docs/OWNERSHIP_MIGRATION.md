---
title: Recipe Ownership Migration
description: Production rollout, rollback, and recovery guide for strict recipe ownership
ms.date: 2026-09-28
ms.topic: how-to
---

## Purpose

Migration `20260928_19` makes recipe and ingredient ownership mandatory. It
assigns an owner only when one distinct user references a legacy recipe through
meal history. It quarantines ambiguous and unreferenced records instead of
guessing an owner.

Run this migration only after reviewing the inventory and creating a verified
database backup.

## Preflight inventory

Inventory every ownerless recipe and its deterministic disposition:

```sql
WITH ownership_evidence AS (
    SELECT
        r.id,
        r.name,
        COUNT(DISTINCT m.user_id) AS distinct_users,
        ARRAY_AGG(DISTINCT m.user_id)
            FILTER (WHERE m.user_id IS NOT NULL) AS candidate_users
    FROM recipe_names AS r
    LEFT JOIN meal_history AS m ON m.recipe_id = r.id
    WHERE r.user_id IS NULL
    GROUP BY r.id, r.name
)
SELECT
    id,
    name,
    distinct_users,
    candidate_users,
    CASE
        WHEN distinct_users = 1 THEN 'assign unique meal-history user'
        WHEN distinct_users = 0 THEN 'quarantine unreferenced recipe'
        ELSE 'quarantine ambiguous recipe'
    END AS disposition
FROM ownership_evidence
ORDER BY disposition, name, id;
```

Inventory ownerless ingredients and their linked recipe owners:

```sql
SELECT
    i.id,
    i.ingredient_name,
    ARRAY_AGG(DISTINCT r.user_id)
        FILTER (WHERE r.user_id IS NOT NULL) AS linked_recipe_owners,
    COUNT(DISTINCT ri.recipe_id) AS linked_recipes
FROM ingredient_names AS i
LEFT JOIN recipe_ingredients AS ri ON ri.ingredient_id = i.id
LEFT JOIN recipe_names AS r ON r.id = ri.recipe_id
WHERE i.user_id IS NULL
GROUP BY i.id, i.ingredient_name
ORDER BY i.ingredient_name, i.id;
```

Save both result sets with the deployment evidence. Investigate unexpected
owners or counts before continuing.

## Backup gate

Create and verify a backup before applying the migration:

```bash
make db-backup
```

Confirm that the backup can be located and restored according to the deployment
runbook. Do not continue when the inventory or backup is incomplete.

## Upgrade

Apply the migration through the normal deployment workflow:

```bash
make migrate-prod
```

The migration performs these operations in one transaction:

1. Record recipes with exactly one distinct meal-history user and assign that
   owner.
2. Snapshot and clear meal links whose user differs from an owned recipe.
3. Snapshot unresolved recipes, recipe-ingredient links, and meal-to-recipe
   links in `ownership_*` recovery tables.
4. Clear quarantined meal references before removing unresolved recipes.
5. Copy or reuse ingredients for each resolved recipe owner and repoint links.
6. Snapshot and remove remaining ownerless ingredients.
7. Verify zero null owners and apply non-null constraints.

## Post-upgrade verification

Both counts must be zero:

```sql
SELECT COUNT(*) AS ownerless_recipes
FROM recipe_names
WHERE user_id IS NULL;

SELECT COUNT(*) AS ownerless_ingredients
FROM ingredient_names
WHERE user_id IS NULL;
```

Confirm the constraints:

```sql
SELECT table_name, column_name, is_nullable
FROM information_schema.columns
WHERE (table_name, column_name) IN (
    ('recipe_names', 'user_id'),
    ('ingredient_names', 'user_id')
)
ORDER BY table_name;
```

`is_nullable` must be `NO` for both rows.

Review quarantine counts:

```sql
SELECT 'recipes' AS record_type, COUNT(*) FROM ownership_recipe_quarantine
UNION ALL
SELECT 'ingredients', COUNT(*) FROM ownership_ingredient_quarantine
UNION ALL
SELECT 'recipe ingredients', COUNT(*)
FROM ownership_recipe_ingredient_quarantine
UNION ALL
SELECT 'meal links', COUNT(*) FROM ownership_meal_link_quarantine;
```

## Rollback behavior

Downgrade only when application compatibility and operational review require
it:

```bash
cd apps/backend
uv run alembic -c src/alembic.ini downgrade 20260131_18
```

The downgrade:

1. Makes both ownership columns nullable.
2. Restores quarantined ingredients and recipes.
3. Repoints migrated recipe-ingredient links to their original ingredients.
4. Restores quarantined recipe-ingredient links.
5. Restores each saved `meal_history.recipe_id`.
6. Returns inferred recipe and ingredient ownership to its legacy state.
7. Removes recovery tables after restoration completes.

Application authorization denies null-owned resources even after rollback.
Rollback restores data but does not restore the former compatibility access
path.

## Manual recovery while upgraded

Prefer correcting a quarantined recipe by assigning an operator-confirmed user
and reinserting it with non-null ownership. Restore dependencies in this order:

1. Recipe and ingredient domain rows
2. Recipe-ingredient association rows
3. `meal_history.recipe_id` links

Use the `payload` values in `ownership_recipe_quarantine`,
`ownership_ingredient_quarantine`, and
`ownership_recipe_ingredient_quarantine`. Use `meal_id` and `recipe_id` from
`ownership_meal_link_quarantine`.

Test recovery SQL in a restored backup before production execution. Keep the
quarantine tables until the production inventory, application checks, and
recovery review are complete.

## Validation

The canonical migration check stages owned, uniquely inferable, ambiguous, and
unreferenced records. It verifies upgrade, downgrade recovery, and fresh
development initialization:

```bash
make check-migrations
```

Run the full repository checks before deployment:

```bash
make check
make test
```
