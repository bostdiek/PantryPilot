import type { ComponentType, ReactNode, SVGProps } from 'react';

type SvgComponent = ComponentType<SVGProps<SVGSVGElement>>;

interface IconProps {
  /**
   * Inline SVG component (preferred). Use `import Icon from '...svg?react'` or SVGR default export.
   */
  svg?: SvgComponent;
  /**
   * Image source fallback (png/jpg/svg). Tailwind color utilities will not apply to <img>.
   */
  src?: string;
  className?: string;
  alt?: string;
  /**
   * Optional title/accessible label for inline SVGs.
   */
  title?: string;
  children?: ReactNode;
  /**
   * Test ID for testing environments
   */
  testId?: string;
}

/**
 * Icon component that renders SVG icons
 *
 * @example
 * ```tsx
 * <Icon src="/src/components/ui/icons/check.svg" className="h-5 w-5" />
 * ```
 */
export function Icon({
  svg: Svg,
  src,
  className = 'h-5 w-5',
  alt = '',
  title,
  children,
  testId,
}: IconProps) {
  // In test environment (Vitest sets import.meta.env.MODE to 'test')
  const isTestEnv = import.meta.env.MODE === 'test';

  // Handle test environment without SVG imports
  if (isTestEnv && !Svg && !src) {
    return (
      <svg
        className={className}
        data-testid={testId || 'mock-icon'}
        aria-hidden={!alt && !title}
        role={alt || title ? 'img' : undefined}
      >
        {title || alt ? <title>{title || alt}</title> : null}
        {children}
      </svg>
    );
  }

  if (Svg) {
    return (
      <Svg
        className={className}
        aria-hidden={!alt && !title}
        role={alt || title ? 'img' : undefined}
        data-testid={testId}
      >
        {title || alt ? <title>{title || alt}</title> : null}
        {children}
      </Svg>
    );
  }

  if (src) {
    return (
      <img
        src={src}
        className={className}
        aria-hidden={!alt}
        alt={alt || undefined}
        data-testid={testId}
      />
    );
  }

  return null;
}
