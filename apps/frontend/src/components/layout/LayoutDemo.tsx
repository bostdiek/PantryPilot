import React from 'react';
import { Grid } from './Grid';
import { Stack } from './Stack';

/**
 * LayoutDemo component showcases Grid and Stack layout components
 */
export const LayoutDemo: React.FC = () => (
  <div className="space-y-8 p-6">
    <section>
      <h2 className="mb-4 text-lg font-semibold">Grid Layout</h2>
      <Grid columns={3} gap={4} className="bg-gray-50 p-4">
        {[1, 2, 3, 4, 5, 6].map((n) => (
          <div
            key={n}
            className="border bg-white p-4 text-center text-gray-700"
          >
            Item {n}
          </div>
        ))}
      </Grid>
    </section>

    <section>
      <h2 className="mb-4 text-lg font-semibold">Stack Layout</h2>
      <Stack direction="horizontal" gap={4} className="bg-gray-50 p-4">
        <div className="border bg-white p-4 text-gray-700">First</div>
        <div className="border bg-white p-4 text-gray-700">Second</div>
        <div className="border bg-white p-4 text-gray-700">Third</div>
      </Stack>
      <Stack direction="vertical" gap={2} className="mt-6 bg-gray-50 p-4">
        <div className="border bg-white p-4 text-gray-700">Top</div>
        <div className="border bg-white p-4 text-gray-700">Middle</div>
        <div className="border bg-white p-4 text-gray-700">Bottom</div>
      </Stack>
    </section>
  </div>
);
