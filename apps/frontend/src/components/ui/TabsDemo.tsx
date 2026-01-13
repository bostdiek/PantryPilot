import { useState } from 'react';
import { Tabs } from './Tabs';

/**
 * TabsDemo component that demonstrates the usage of our Tabs component
 */
export function TabsDemo() {
  // Basic tabs data
  const recipeTabs = [
    {
      id: 'ingredients',
      label: 'Ingredients',
      content: (
        <ul className="list-disc space-y-1 pl-5">
          <li>2 cups all-purpose flour</li>
          <li>1 teaspoon baking powder</li>
          <li>1/2 teaspoon salt</li>
          <li>1 cup sugar</li>
          <li>1/2 cup butter, softened</li>
          <li>2 eggs</li>
          <li>1 teaspoon vanilla extract</li>
          <li>1/2 cup milk</li>
        </ul>
      ),
    },
    {
      id: 'instructions',
      label: 'Instructions',
      content: (
        <ol className="list-decimal space-y-2 pl-5">
          <li>Preheat oven to 350°F (175°C).</li>
          <li>
            In a medium bowl, combine flour, baking powder, and salt; set aside.
          </li>
          <li>
            In a large bowl, cream together butter and sugar until light and
            fluffy.
          </li>
          <li>
            Beat in eggs one at a time, then stir in vanilla. Gradually blend in
            the dry ingredients.
          </li>
          <li>
            Pour batter into a greased 9-inch cake pan and bake for 30-35
            minutes.
          </li>
          <li>Allow to cool before serving.</li>
        </ol>
      ),
    },
    {
      id: 'notes',
      label: 'Notes',
      content: (
        <div className="space-y-2">
          <p>
            This basic cake recipe can be customized with different flavorings:
          </p>
          <ul className="list-disc pl-5">
            <li>
              Add 1/2 cup of cocoa powder for a chocolate version (reduce flour
              by 1/2 cup)
            </li>
            <li>
              Add 2 tablespoons of lemon zest and substitute lemon juice for
              vanilla for a lemon cake
            </li>
            <li>Fold in 1 cup of fresh berries for a fruit-filled variation</li>
          </ul>
        </div>
      ),
    },
  ];

  // For controlled tabs example
  const [selectedTabIndex, setSelectedTabIndex] = useState(0);
  const profileTabs = [
    {
      id: 'account',
      label: 'Account',
      content: (
        <div className="space-y-4">
          <h3 className="text-lg font-medium">Account Settings</h3>
          <div className="space-y-2">
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Name
              </label>
              <input
                type="text"
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
                defaultValue="John Doe"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Email
              </label>
              <input
                type="email"
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
                defaultValue="john.doe@example.com"
              />
            </div>
          </div>
        </div>
      ),
    },
    {
      id: 'preferences',
      label: 'Preferences',
      content: (
        <div className="space-y-4">
          <h3 className="text-lg font-medium">User Preferences</h3>
          <div className="space-y-2">
            <div className="flex items-center">
              <input
                id="dark-mode"
                type="checkbox"
                className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <label
                htmlFor="dark-mode"
                className="ml-2 block text-sm text-gray-700"
              >
                Dark Mode
              </label>
            </div>
            <div className="flex items-center">
              <input
                id="notifications"
                type="checkbox"
                className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                defaultChecked
              />
              <label
                htmlFor="notifications"
                className="ml-2 block text-sm text-gray-700"
              >
                Enable Notifications
              </label>
            </div>
          </div>
        </div>
      ),
    },
    {
      id: 'privacy',
      label: 'Privacy',
      content: (
        <div className="space-y-4">
          <h3 className="text-lg font-medium">Privacy Settings</h3>
          <div className="space-y-2">
            <div className="flex items-center">
              <input
                id="public-profile"
                type="checkbox"
                className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <label
                htmlFor="public-profile"
                className="ml-2 block text-sm text-gray-700"
              >
                Public Profile
              </label>
            </div>
            <div className="flex items-center">
              <input
                id="share-recipes"
                type="checkbox"
                className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                defaultChecked
              />
              <label
                htmlFor="share-recipes"
                className="ml-2 block text-sm text-gray-700"
              >
                Share My Recipes
              </label>
            </div>
          </div>
        </div>
      ),
    },
  ];

  // Tabs with disabled tab
  const dashboardTabs = [
    {
      id: 'overview',
      label: 'Overview',
      content: (
        <div>
          <h3 className="text-lg font-medium">Dashboard Overview</h3>
          <p className="mt-2">
            Welcome to your Smart Meal Planner dashboard. Here you can see an
            overview of your recipes, meal plans, and shopping lists.
          </p>
          <div className="mt-4 grid grid-cols-3 gap-4">
            <div className="rounded-md bg-blue-50 p-4">
              <h4 className="font-medium text-blue-700">Total Recipes</h4>
              <p className="mt-2 text-2xl font-bold">24</p>
            </div>
            <div className="rounded-md bg-green-50 p-4">
              <h4 className="font-medium text-green-700">Planned Meals</h4>
              <p className="mt-2 text-2xl font-bold">14</p>
            </div>
            <div className="rounded-md bg-purple-50 p-4">
              <h4 className="font-medium text-purple-700">Shopping Items</h4>
              <p className="mt-2 text-2xl font-bold">37</p>
            </div>
          </div>
        </div>
      ),
    },
    {
      id: 'analytics',
      label: 'Analytics',
      content: (
        <div>
          <h3 className="text-lg font-medium">Usage Analytics</h3>
          <p className="mt-2">
            Track your cooking habits and meal planning statistics.
          </p>
          <div className="mt-4 flex h-40 items-center justify-center rounded-md bg-gray-100">
            [Analytics Chart Placeholder]
          </div>
        </div>
      ),
    },
    {
      id: 'reports',
      label: 'Reports',
      disabled: true,
      content: (
        <div>
          <h3 className="text-lg font-medium">Reports</h3>
          <p>This section is coming soon!</p>
        </div>
      ),
    },
  ];

  // Vertical tabs example
  const helpTabs = [
    {
      id: 'getting-started',
      label: 'Getting Started',
      content: (
        <div>
          <h3 className="text-lg font-medium">
            Getting Started with Smart Meal Planner
          </h3>
          <p className="mt-2">
            Smart Meal Planner makes meal planning and recipe management simple.
            Follow these steps to get started:
          </p>
          <ol className="mt-4 list-decimal space-y-2 pl-5">
            <li>Create your account or sign in</li>
            <li>Add your favorite recipes to your collection</li>
            <li>Plan your meals for the week</li>
            <li>Generate your shopping list</li>
            <li>Start cooking!</li>
          </ol>
        </div>
      ),
    },
    {
      id: 'faq',
      label: 'FAQ',
      content: (
        <div>
          <h3 className="text-lg font-medium">Frequently Asked Questions</h3>
          <div className="mt-4 space-y-4">
            <div>
              <h4 className="font-medium">How do I create a new recipe?</h4>
              <p className="mt-1 text-gray-600">
                Navigate to the Recipes page and click the "Add Recipe" button.
                Fill out the form with your recipe details.
              </p>
            </div>
            <div>
              <h4 className="font-medium">
                Can I import recipes from other websites?
              </h4>
              <p className="mt-1 text-gray-600">
                Yes! Smart Meal Planner allows you to import recipes by pasting
                a URL from supported recipe websites.
              </p>
            </div>
            <div>
              <h4 className="font-medium">
                How do I generate a shopping list?
              </h4>
              <p className="mt-1 text-gray-600">
                After creating your weekly meal plan, go to the Shopping List
                page and click "Generate List".
              </p>
            </div>
          </div>
        </div>
      ),
    },
    {
      id: 'contact',
      label: 'Contact Support',
      content: (
        <div>
          <h3 className="text-lg font-medium">Contact Support</h3>
          <p className="mt-2">
            Need help? Our support team is ready to assist you.
          </p>
          <form className="mt-4 space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Subject
              </label>
              <input
                type="text"
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Message
              </label>
              <textarea
                rows={4}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
              ></textarea>
            </div>
            <button
              type="button"
              className="rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
            >
              Send Message
            </button>
          </form>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-12 p-6">
      {/* Basic Tabs */}
      <section>
        <h2 className="mb-4 text-lg font-semibold">Basic Tabs</h2>
        <div className="bg-white">
          <Tabs
            tabs={recipeTabs}
            className="rounded-md border border-gray-200 p-4"
          />
        </div>
      </section>

      {/* Controlled Tabs */}
      <section>
        <h2 className="mb-4 text-lg font-semibold">Controlled Tabs</h2>
        <div className="mb-4">
          <p className="text-sm text-gray-600">
            Current tab: {profileTabs[selectedTabIndex].label}
          </p>
          <div className="mt-2 flex space-x-2">
            <button
              onClick={() => setSelectedTabIndex(0)}
              className="rounded-md bg-blue-600 px-3 py-1 text-sm text-white hover:bg-blue-700"
            >
              Go to Account
            </button>
            <button
              onClick={() => setSelectedTabIndex(1)}
              className="rounded-md bg-blue-600 px-3 py-1 text-sm text-white hover:bg-blue-700"
            >
              Go to Preferences
            </button>
            <button
              onClick={() => setSelectedTabIndex(2)}
              className="rounded-md bg-blue-600 px-3 py-1 text-sm text-white hover:bg-blue-700"
            >
              Go to Privacy
            </button>
          </div>
        </div>
        <div className="bg-white">
          <Tabs
            tabs={profileTabs}
            selectedIndex={selectedTabIndex}
            onChange={setSelectedTabIndex}
            className="rounded-md border border-gray-200 p-4"
          />
        </div>
      </section>

      {/* Tabs with Disabled Tab */}
      <section>
        <h2 className="mb-4 text-lg font-semibold">Tabs with Disabled Tab</h2>
        <div className="bg-white">
          <Tabs
            tabs={dashboardTabs}
            className="rounded-md border border-gray-200 p-4"
            selectedTabClassName="bg-blue-50"
          />
        </div>
      </section>

      {/* Vertical Tabs */}
      <section>
        <h2 className="mb-4 text-lg font-semibold">Vertical Tabs</h2>
        <div className="bg-white">
          <Tabs
            tabs={helpTabs}
            vertical
            className="grid grid-cols-4 gap-4 rounded-md border border-gray-200 p-4"
            tabListClassName="col-span-1"
            panelsClassName="col-span-3 border-l border-gray-200 pl-4"
            tabClassName="pl-4"
            selectedTabClassName="bg-blue-50"
          />
        </div>
      </section>
    </div>
  );
}
