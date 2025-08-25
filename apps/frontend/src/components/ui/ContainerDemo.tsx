import React from 'react';
import { Card } from './Card';
import { Container } from './Container';

/**
 * Demo component for Container
 * Displays various container sizes, layouts, and usage examples
 */
export const ContainerDemo: React.FC = () => {
  return (
    <div className="space-y-8">
      {/* Container Sizes */}
      <div className="space-y-4">
        <h3 className="text-lg font-medium text-gray-700">Container Sizes</h3>
        <div className="space-y-4">
          <div className="border-2 border-dashed border-blue-200 p-2">
            <Container size="sm" className="bg-blue-50 py-3 text-center">
              <p>Small Container (640px)</p>
            </Container>
          </div>

          <div className="border-2 border-dashed border-blue-200 p-2">
            <Container size="md" className="bg-blue-50 py-3 text-center">
              <p>Medium Container (768px)</p>
            </Container>
          </div>

          <div className="border-2 border-dashed border-blue-200 p-2">
            <Container size="lg" className="bg-blue-50 py-3 text-center">
              <p>Large Container (1024px) - Default</p>
            </Container>
          </div>

          <div className="border-2 border-dashed border-blue-200 p-2">
            <Container size="xl" className="bg-blue-50 py-3 text-center">
              <p>Extra Large Container (1280px)</p>
            </Container>
          </div>

          <div className="border-2 border-dashed border-blue-200 p-2">
            <Container size="full" className="bg-blue-50 py-3 text-center">
              <p>Full Width Container</p>
            </Container>
          </div>
        </div>
      </div>

      {/* Container Options */}
      <div className="space-y-4">
        <h3 className="text-lg font-medium text-gray-700">Container Options</h3>
        <div className="space-y-4">
          <div className="border-2 border-dashed border-blue-200 p-2">
            <Container centered={false} className="bg-blue-50 py-3">
              <p>Container without centering</p>
            </Container>
          </div>

          <div className="border-2 border-dashed border-blue-200 p-2">
            <Container padding={false} className="bg-blue-50 py-3 text-center">
              <p>Container without padding</p>
            </Container>
          </div>
        </div>
      </div>

      {/* HTML Tag Variations */}
      <div className="space-y-4">
        <h3 className="text-lg font-medium text-gray-700">
          HTML Tag Variations
        </h3>
        <div className="space-y-4">
          <div className="border-2 border-dashed border-blue-200 p-2">
            <Container as="section" className="bg-blue-50 py-3 text-center">
              <p>&lt;section&gt; Container</p>
            </Container>
          </div>

          <div className="border-2 border-dashed border-blue-200 p-2">
            <Container as="article" className="bg-blue-50 py-3 text-center">
              <p>&lt;article&gt; Container</p>
            </Container>
          </div>

          <div className="border-2 border-dashed border-blue-200 p-2">
            <Container as="main" className="bg-blue-50 py-3 text-center">
              <p>&lt;main&gt; Container</p>
            </Container>
          </div>
        </div>
      </div>

      {/* Practical Examples */}
      <div className="space-y-4">
        <h3 className="text-lg font-medium text-gray-700">
          Practical Examples
        </h3>
        <div className="space-y-4">
          <Container>
            <Card title="Blog Post Layout Example">
              <div className="prose">
                <h1>Using Containers for Layout</h1>
                <p>
                  Containers help maintain consistent layouts across your
                  application. They're especially useful for content-heavy pages
                  like blog posts, articles, or documentation.
                </p>
                <p>
                  By setting different container sizes, you can control the
                  reading experience based on the content type. Smaller
                  containers (like size="md") are great for text-heavy content,
                  while larger containers work better for dashboards or grid
                  layouts.
                </p>
              </div>
            </Card>
          </Container>

          <Container size="xl">
            <h4 className="mb-4 text-lg font-medium">
              Dashboard Layout Example
            </h4>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <Card title="Statistics">
                <div className="flex h-48 items-center justify-center">
                  <p>Dashboard stats would go here</p>
                </div>
              </Card>
              <Card title="Recent Activity">
                <div className="flex h-48 items-center justify-center">
                  <p>Activity feed would go here</p>
                </div>
              </Card>
              <Card title="Quick Actions">
                <div className="flex h-48 items-center justify-center">
                  <p>Action buttons would go here</p>
                </div>
              </Card>
            </div>
          </Container>
        </div>
      </div>
    </div>
  );
};
