import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { Badge } from '../Badge';

describe('Badge', () => {
  it('renders children correctly', () => {
    render(<Badge>Test Badge</Badge>);
    expect(screen.getByText('Test Badge')).toBeInTheDocument();
  });

  it('applies secondary variant by default', () => {
    const { container } = render(<Badge>Default</Badge>);
    const badge = container.firstChild as HTMLElement;
    expect(badge).toHaveClass('bg-gray-100', 'text-gray-800');
  });

  it('applies primary variant styles', () => {
    const { container } = render(<Badge variant="primary">Primary</Badge>);
    const badge = container.firstChild as HTMLElement;
    expect(badge).toHaveClass('bg-primary-100', 'text-primary-800');
  });

  it('applies success variant styles', () => {
    const { container } = render(<Badge variant="success">Success</Badge>);
    const badge = container.firstChild as HTMLElement;
    expect(badge).toHaveClass('bg-green-100', 'text-green-800');
  });

  it('applies warning variant styles', () => {
    const { container } = render(<Badge variant="warning">Warning</Badge>);
    const badge = container.firstChild as HTMLElement;
    expect(badge).toHaveClass('bg-yellow-100', 'text-yellow-800');
  });

  it('applies danger variant styles', () => {
    const { container } = render(<Badge variant="danger">Danger</Badge>);
    const badge = container.firstChild as HTMLElement;
    expect(badge).toHaveClass('bg-red-100', 'text-red-800');
  });

  it('applies additional className', () => {
    const { container } = render(
      <Badge className="custom-class">Custom</Badge>
    );
    const badge = container.firstChild as HTMLElement;
    expect(badge).toHaveClass('custom-class');
  });

  it('renders with complex children', () => {
    render(
      <Badge>
        <span>3</span> meals
      </Badge>
    );
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText('meals')).toBeInTheDocument();
  });
});
