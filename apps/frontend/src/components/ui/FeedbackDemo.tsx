import React from 'react';
import { EmptyState } from './EmptyState';
import { ErrorMessage } from './ErrorMessage';
import { LoadingSpinner } from './LoadingSpinner';

/**
 * FeedbackDemo component showcases loading, error, and empty state components
 */
export const FeedbackDemo: React.FC = () => (
  <div className="space-y-8 p-6">
    {/* Loading Spinner */}
    <section>
      <h2 className="mb-4 text-lg font-semibold">Loading Spinner</h2>
      <LoadingSpinner />
    </section>

    {/* Error Message */}
    <section>
      <h2 className="mb-4 text-lg font-semibold">Error Message</h2>
      <ErrorMessage message="Unable to fetch data." />
    </section>

    {/* Empty State */}
    <section>
      <h2 className="mb-4 text-lg font-semibold">Empty State</h2>
      <EmptyState message="No data available." />
    </section>
  </div>
);
