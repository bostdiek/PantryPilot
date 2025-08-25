import React from 'react';

/**
 * EmptyState component displays when no data is available
 */
interface EmptyStateProps {
  message?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  message = 'No data available.',
}) => (
  <div className="flex flex-col items-center justify-center space-y-2">
    <svg
      className="h-12 w-12 text-gray-400"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
    >
      <path className="stroke-current stroke-2" d="M3 3h18v18H3V3z" />
      <path className="stroke-current stroke-2" d="M8 8h8M8 12h8M8 16h8" />
    </svg>
    <p className="text-lg text-gray-500">{message}</p>
  </div>
);
