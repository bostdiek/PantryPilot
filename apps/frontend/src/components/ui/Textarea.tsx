import clsx from 'clsx';
import React from 'react';

export interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  /** When true (default), apply focus styles */
  focus?: boolean;
}

/**
 * Reusable textarea with consistent styling across the app.
 * Accepts all native textarea props and an optional `focus` boolean
 * to toggle focus ring styles (useful for modal previews where focus
 * ring might be undesirable).
 */
export function Textarea({
  focus = true,
  className = '',
  ...props
}: TextareaProps) {
  const base =
    'resize-vertical w-full rounded-md border-gray-300 px-3 py-2 text-base leading-relaxed whitespace-normal';
  const focusClass = 'focus:border-blue-500 focus:ring-2 focus:ring-blue-500';

  return (
    <textarea
      className={clsx(base, focus && focusClass, className)}
      {...props}
    />
  );
}
