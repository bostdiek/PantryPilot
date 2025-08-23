import React from 'react';
import { Button } from './Button';
import { Card } from './Card';

/**
 * Demo component for Card
 * Displays various card variants, layouts, and states
 */
export const CardDemo: React.FC = () => {
  return (
    <div className="space-y-8">
      {/* Basic Cards */}
      <div className="space-y-4">
        <h3 className="text-lg font-medium text-gray-700">Basic Cards</h3>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Card>
            <p>A simple card with default styling</p>
          </Card>

          <Card title="Card with Title">
            <p>This card includes a title in the header</p>
          </Card>
        </div>
      </div>

      {/* Card Variants */}
      <div className="space-y-4">
        <h3 className="text-lg font-medium text-gray-700">Card Variants</h3>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <Card variant="default" title="Default Card">
            <p>The standard card with a light border</p>
          </Card>

          <Card variant="outlined" title="Outlined Card">
            <p>Card with a more prominent border</p>
          </Card>

          <Card variant="elevated" title="Elevated Card">
            <p>Card with a shadow for emphasis</p>
          </Card>
        </div>
      </div>

      {/* Cards with Actions */}
      <div className="space-y-4">
        <h3 className="text-lg font-medium text-gray-700">
          Cards with Actions
        </h3>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Card
            title="Header Actions"
            headerActions={
              <Button variant="outline" size="sm">
                View All
              </Button>
            }
          >
            <p>This card has actions in the header</p>
          </Card>

          <Card
            title="With Footer"
            footer={
              <div className="flex justify-end space-x-2">
                <Button variant="outline" size="sm">
                  Cancel
                </Button>
                <Button variant="primary" size="sm">
                  Save
                </Button>
              </div>
            }
          >
            <p>This card has a footer with actions</p>
          </Card>
        </div>
      </div>

      {/* Layout Options */}
      <div className="space-y-4">
        <h3 className="text-lg font-medium text-gray-700">Layout Options</h3>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Card title="No Padding" noPadding>
            <img
              src="https://images.unsplash.com/photo-1546069901-ba9599a7e63c"
              alt="Food"
              className="h-48 w-full object-cover"
            />
            <div className="p-4">
              <p>Card with no padding, useful for images</p>
            </div>
          </Card>

          <div className="h-64">
            <Card title="Full Height & Width" fullWidth fullHeight>
              <div className="flex h-full items-center justify-center">
                <p>This card takes up the full height and width</p>
              </div>
            </Card>
          </div>
        </div>
      </div>

      {/* Interactive Card */}
      <div className="space-y-4">
        <h3 className="text-lg font-medium text-gray-700">Interactive Card</h3>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Card
            variant="elevated"
            onClick={() => alert('Card clicked!')}
            className="cursor-pointer transition-transform hover:scale-105"
          >
            <div className="p-6 text-center">
              <p className="text-lg font-medium">Clickable Card</p>
              <p className="mt-2 text-gray-500">
                Click me to trigger an action
              </p>
            </div>
          </Card>

          <Card title="Recipe Card Example" variant="elevated" noPadding>
            <img
              src="https://images.unsplash.com/photo-1512621776951-a57141f2eefd"
              alt="Healthy Salad"
              className="h-48 w-full object-cover"
            />
            <div className="p-4">
              <h4 className="mb-2 text-lg font-medium">Summer Salad</h4>
              <p className="mb-4 text-gray-600">
                A fresh and healthy summer salad with mixed greens, tomatoes,
                and avocado.
              </p>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-500">20 min prep time</span>
                <Button variant="outline" size="sm">
                  View Recipe
                </Button>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};
