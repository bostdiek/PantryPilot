import type { ElementType, ReactNode } from 'react';
import { forwardRef } from 'react';

export type ContainerSize = 'sm' | 'md' | 'lg' | 'xl' | 'full';

export interface ContainerProps {
  /**
   * Container content
   */
  children: ReactNode;

  /**
   * Container max width
   * @default 'lg'
   */
  size?: ContainerSize;

  /**
   * Centers the container horizontally
   * @default true
   */
  centered?: boolean;

  /**
   * Adds padding to the container
   * @default true
   */
  padding?: boolean;

  /**
   * Additional CSS classes
   */
  className?: string;

  /**
   * HTML tag to use for the container
   * @default 'div'
   */
  as?: 'div' | 'section' | 'article' | 'main';
}

/**
 * Container component for centered, responsive content
 *
 * @example
 * ```tsx
 * <Container size="md">
 *   <p>Content goes here</p>
 * </Container>
 * ```
 */
export const Container = forwardRef<HTMLDivElement, ContainerProps>(
  (
    {
      children,
      size = 'lg',
      centered = true,
      padding = true,
      className = '',
      as = 'div',
      ...props
    },
    ref
  ) => {
    // Size styles (max-width)
    const sizeStyles = {
      sm: 'max-w-screen-sm',
      md: 'max-w-screen-md',
      lg: 'max-w-screen-lg',
      xl: 'max-w-screen-xl',
      full: 'max-w-full',
    };

    // Combined styles
    const combinedStyles = [
      'w-full',
      sizeStyles[size],
      centered ? 'mx-auto' : '',
      padding ? 'px-4 sm:px-6 md:px-8' : '',
      className,
    ]
      .filter(Boolean)
      .join(' ');

    const Component = as as ElementType;

    return (
      <Component
        className={combinedStyles}
        // Use type assertion for the ref to work with different HTML elements
        ref={ref as any}
        {...props}
      >
        {children}
      </Component>
    );
  }
);

Container.displayName = 'Container';
