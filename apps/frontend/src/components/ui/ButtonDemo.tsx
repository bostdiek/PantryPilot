import { kitchenIcon, restaurantIcon } from '.';
import { Button } from './Button';

/**
 * ButtonDemo component that demonstrates the usage of our Button component
 */
export function ButtonDemo() {
  return (
    <div className="space-y-8 p-6">
      {/* Variants */}
      <section>
        <h2 className="mb-4 text-lg font-semibold">Button Variants</h2>
        <div className="flex flex-wrap gap-4">
          <Button variant="primary">Primary</Button>
          <Button variant="secondary">Secondary</Button>
          <Button variant="danger">Danger</Button>
          <Button variant="outline">Outline</Button>
          <Button variant="ghost">Ghost</Button>
        </div>
      </section>

      {/* Sizes */}
      <section>
        <h2 className="mb-4 text-lg font-semibold">Button Sizes</h2>
        <div className="flex flex-wrap items-center gap-4">
          <Button size="sm">Small</Button>
          <Button size="md">Medium</Button>
          <Button size="lg">Large</Button>
        </div>
      </section>

      {/* With Icons */}
      <section>
        <h2 className="mb-4 text-lg font-semibold">Buttons with Icons</h2>
        <div className="flex flex-wrap gap-4">
          <Button leftIcon={kitchenIcon}>Left Icon</Button>
          <Button rightIcon={restaurantIcon}>Right Icon</Button>
          <Button leftIcon={kitchenIcon} rightIcon={restaurantIcon}>
            Both Icons
          </Button>
        </div>
      </section>

      {/* States */}
      <section>
        <h2 className="mb-4 text-lg font-semibold">Button States</h2>
        <div className="flex flex-wrap gap-4">
          <Button disabled>Disabled</Button>
          <Button loading>Loading</Button>
          <Button variant="primary" fullWidth>
            Full Width
          </Button>
        </div>
      </section>
    </div>
  );
}
