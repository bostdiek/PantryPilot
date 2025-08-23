import { useState } from 'react';
import { Disclosure } from './Disclosure';

/**
 * DisclosureDemo component that demonstrates the usage of our Disclosure component
 */
export function DisclosureDemo() {
  // Track state changes from onChange as an example (Disclosure is uncontrolled)
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="space-y-8 p-6">
      {/* Basic Disclosure */}
      <section>
        <h2 className="mb-4 text-lg font-semibold">Basic Disclosure</h2>
        <Disclosure title="What is PantryPilot?">
          <p>
            PantryPilot is a meal planning application that helps you organize
            your recipes, plan your weekly meals, and generate shopping lists
            automatically.
          </p>
        </Disclosure>
      </section>

      {/* Multiple Disclosures (FAQ Style) */}
      <section>
        <h2 className="mb-4 text-lg font-semibold">FAQ Style Disclosures</h2>
        <div className="space-y-2">
          <Disclosure title="How do I create a new recipe?">
            <p>
              To create a new recipe, navigate to the Recipes page and click the
              "Add Recipe" button. Fill out the form with your recipe details
              including ingredients, instructions, and cook time.
            </p>
          </Disclosure>

          <Disclosure title="Can I import recipes from other websites?">
            <p>
              Yes! PantryPilot allows you to import recipes by pasting a URL
              from supported recipe websites. The app will automatically extract
              the ingredients, instructions, and other recipe details.
            </p>
          </Disclosure>

          <Disclosure title="How do I generate a shopping list?">
            <p>
              After creating your weekly meal plan, go to the Shopping List page
              and click "Generate List". PantryPilot will automatically compile
              all the ingredients needed for your planned meals.
            </p>
            <p className="mt-2">
              You can also manually add or remove items from the shopping list.
            </p>
          </Disclosure>
        </div>
      </section>

      {/* Disclosure with Default Open */}
      <section>
        <h2 className="mb-4 text-lg font-semibold">Default Open Disclosure</h2>
        <Disclosure title="Getting Started Guide" defaultOpen>
          <ol className="list-decimal space-y-2 pl-5">
            <li>Create an account or sign in to get started</li>
            <li>Add your favorite recipes to your collection</li>
            <li>
              Plan your meals for the week by dragging recipes to the calendar
            </li>
            <li>Generate your shopping list with a single click</li>
            <li>Check off items as you shop</li>
          </ol>
        </Disclosure>
      </section>

      {/* Observing Disclosure State via onChange */}
      <section>
        <h2 className="mb-4 text-lg font-semibold">State Changes</h2>
        <p className="mb-2 text-sm text-gray-600">
          Current state: {isOpen ? 'Open' : 'Closed'}
        </p>
        <Disclosure
          title="This disclosure reports state via onChange"
          onChange={setIsOpen}
        >
          <p>
            Disclosure is uncontrolled; we listen to changes via onChange to
            keep external state in sync.
          </p>
        </Disclosure>
      </section>

      {/* Custom Styled Disclosure */}
      <section>
        <h2 className="mb-4 text-lg font-semibold">Custom Styled Disclosure</h2>
        <Disclosure
          title="Custom Styling Options"
          buttonClassName="bg-green-50 text-green-900 hover:bg-green-100"
          panelClassName="bg-green-50 rounded-b-lg"
        >
          <p>
            You can customize the appearance of the disclosure by providing
            custom class names for different parts of the component.
          </p>
          <ul className="mt-2 list-disc pl-5">
            <li>
              Use <code>className</code> for the overall container
            </li>
            <li>
              Use <code>buttonClassName</code> for the button/header
            </li>
            <li>
              Use <code>panelClassName</code> for the content panel
            </li>
          </ul>
        </Disclosure>
      </section>
    </div>
  );
}
