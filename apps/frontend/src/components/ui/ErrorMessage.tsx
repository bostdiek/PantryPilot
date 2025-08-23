import React from 'react';

/**
 * ErrorMessage component displays an error message for error states
 */
interface ErrorMessageProps {
  message?: string;
}

export const ErrorMessage: React.FC<ErrorMessageProps> = ({
  message = 'Something went wrong.',
}) => (
  <div className="flex items-center justify-center">
    <p className="font-medium text-red-600">{message}</p>
  </div>
);
