import React from 'react';
import { Link } from 'react-router-dom';
import { Grid } from '../components/layout/Grid';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Container } from '../components/ui/Container';
import { Icon } from '../components/ui/Icon';
import CalendarIcon from '../components/ui/icons/calendar.svg?react';
import ChefHatIcon from '../components/ui/icons/chef-hat.svg?react';
import ChevronRightIcon from '../components/ui/icons/chevron-right.svg?react';
import KitchenIcon from '../components/ui/icons/kitchen.svg?react';
import RestaurantIcon from '../components/ui/icons/restaurant.svg?react';
import { useMealPlanStore } from '../stores/useMealPlanStore';
import { useRecipeStore } from '../stores/useRecipeStore';

const HomePage: React.FC = () => {
  // Get data from stores (already loaded by the route loader)
  const { recipes, isLoading: recipesLoading } = useRecipeStore();
  const { currentWeek, isLoading: mealPlanLoading } = useMealPlanStore();

  // Get today's meal plan
  const today = new Date().toLocaleDateString('en-US', { weekday: 'long' });
  const todaysMeal = currentWeek?.days.find((day) => day.day === today);

  return (
    <Container>
      <div className="flex items-center justify-between pt-6 pb-4">
        <div>
          <h1 className="text-2xl font-bold">Hi, demo!</h1>
          <p className="text-gray-600">Ready to plan some meals?</p>
        </div>
        <Link to="/profile" className="ml-auto">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gray-200 text-lg font-bold text-gray-700">
            D
          </div>
        </Link>
      </div>

      <Grid columns={2} gap={6} className="mb-6">
        {/* Recipe Stats Card */}
        <Card variant="elevated" className="h-full">
          {recipesLoading ? (
            <div className="flex h-32 items-center justify-center">
              <div className="border-primary-500 h-8 w-8 animate-spin rounded-full border-4 border-t-transparent"></div>
            </div>
          ) : (
            <div className="flex items-center p-2">
              <div className="mr-4 flex h-12 w-12 items-center justify-center rounded-full bg-gray-100 text-gray-700">
                <Icon svg={KitchenIcon} className="h-6 w-6" />
              </div>
              <div>
                <div className="text-3xl font-bold">{recipes.length}</div>
                <div className="text-gray-600">Recipes</div>
              </div>
            </div>
          )}
        </Card>

        {/* Weekly Plan Card */}
        <Card variant="elevated" className="h-full">
          {mealPlanLoading ? (
            <div className="flex h-32 items-center justify-center">
              <div className="border-primary-500 h-8 w-8 animate-spin rounded-full border-4 border-t-transparent"></div>
            </div>
          ) : (
            <div className="flex items-center p-2">
              <div className="mr-4 flex h-12 w-12 items-center justify-center rounded-full bg-gray-100 text-gray-700">
                <Icon svg={CalendarIcon} className="h-6 w-6" />
              </div>
              <div>
                <div className="text-3xl font-bold">
                  {currentWeek?.days.filter((day) => day.recipe).length || 0}
                </div>
                <div className="text-gray-600">This Week</div>
              </div>
            </div>
          )}
        </Card>
      </Grid>

      {/* Today's Meals Section */}
      <Card variant="elevated" className="mb-6">
        <div className="mb-4 flex items-center">
          <Icon svg={RestaurantIcon} className="mr-2 h-5 w-5 text-gray-700" />
          <h2 className="text-lg font-semibold">Today's Meals</h2>
        </div>{' '}
        {mealPlanLoading ? (
          <div className="flex h-32 items-center justify-center">
            <div className="border-primary-500 h-8 w-8 animate-spin rounded-full border-4 border-t-transparent"></div>
          </div>
        ) : todaysMeal?.recipe ? (
          <div className="p-4">
            <h3 className="mb-1 text-lg font-medium">
              {todaysMeal.recipe.title}
            </h3>
            <p className="mb-4 text-sm text-gray-600">
              Ready in{' '}
              {todaysMeal.recipe.prep_time_minutes +
                todaysMeal.recipe.cook_time_minutes}{' '}
              minutes
            </p>
            <Link to={`/recipes/${todaysMeal.recipe.id}`}>
              <Button variant="outline" fullWidth>
                View Recipe
              </Button>
            </Link>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-8">
            <div className="mb-4 text-6xl text-gray-300">🍽️</div>
            <p className="mb-4 text-center text-gray-600">
              No meals planned for today
            </p>
            <Link to="/meal-plan">
              <Button variant="primary">Plan Today's Meals</Button>
            </Link>
          </div>
        )}
      </Card>

      {/* Quick Actions */}
      <Card variant="elevated" className="mb-6">
        <div className="mb-4 flex items-center">
          <h2 className="text-lg font-semibold">Quick Actions</h2>
        </div>

        <div className="space-y-2">
          <Link
            to="/meal-plan"
            className="flex items-center justify-between rounded-md border border-gray-200 p-3 hover:bg-gray-50"
          >
            <div className="flex items-center">
              <Icon svg={CalendarIcon} className="mr-3 h-5 w-5 text-gray-600" />
              <span>View Meal Planner</span>
            </div>
            <Icon svg={ChevronRightIcon} className="h-5 w-5 text-gray-400" />
          </Link>

          <Link
            to="/recipes/new"
            className="flex items-center justify-between rounded-md border border-gray-200 p-3 hover:bg-gray-50"
          >
            <div className="flex items-center">
              <Icon svg={ChefHatIcon} className="mr-3 h-5 w-5 text-gray-600" />
              <span>Add New Recipe</span>
            </div>
            <Icon svg={ChevronRightIcon} className="h-5 w-5 text-gray-400" />
          </Link>

          <Link
            to="/grocery-list"
            className="flex items-center justify-between rounded-md border border-gray-200 p-3 hover:bg-gray-50"
          >
            <div className="flex items-center">
              <Icon svg={KitchenIcon} className="mr-3 h-5 w-5 text-gray-600" />
              <span>Weekly Grocery List</span>
            </div>
            <Icon svg={ChevronRightIcon} className="h-5 w-5 text-gray-400" />
          </Link>
        </div>
      </Card>
    </Container>
  );
};

export default HomePage;
